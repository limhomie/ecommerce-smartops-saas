"""Knowledge base management endpoints."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel

from src.observability.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    collection: str = "enterprise_wiki"
    top_k: int = 5


class IngestRequest(BaseModel):
    content: str
    collection: str = "enterprise_wiki"
    metadata: dict | None = None


def _get_ltm(request: Request):
    """Get or create a LongTermMemory from app state."""
    if hasattr(request.app.state, "memory_manager"):
        return request.app.state.memory_manager.long_term
    from config.settings import Settings
    from src.memory.long_term import LongTermMemory
    from src.memory.vector_store import VectorStore
    settings: Settings = request.app.state.settings
    store = VectorStore(settings)
    return LongTermMemory(store)


def _content_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()[:16]


def _dedup_check(lt_memory, collection: str, content: str) -> bool:
    """Return True if this content was already ingested (hash match)."""
    h = _content_hash(content)
    try:
        results = lt_memory.search(
            collection, h, top_k=1, threshold=0.01
        )
        return any(d.get("metadata", {}).get("content_hash") == h for d in results)
    except Exception:
        return False


def _extract_pdf_text(content: bytes, filename: str) -> str:
    """Extract text from a PDF using pymupdf4llm (C engine, Markdown output)."""
    import io
    import pymupdf4llm
    md = pymupdf4llm.to_markdown(io.BytesIO(content))
    return f"# {filename}\n\n{md}"


# ── JSON body ingest (text paste) ──

@router.post("/api/knowledge/documents")
async def ingest_document_json(request: Request, body: IngestRequest):
    """Ingest a document from JSON body."""
    try:
        lt_memory = _get_ltm(request)
        if _dedup_check(lt_memory, body.collection, body.content):
            return {"collection": body.collection, "chunks": 0, "status": "duplicate",
                    "message": "内容已存在，跳过重复录入"}

        meta = body.metadata or {"source": "api_paste"}
        meta["content_hash"] = _content_hash(body.content)
        chunks = lt_memory.ingest_document(body.collection, body.content, meta)
        return {"collection": body.collection, "chunks": chunks, "status": "ok"}
    except Exception as e:
        logger.error("ingest_error", error=str(e))
        return {"error": str(e)}, 500


# ── Search ──

@router.get("/api/knowledge/search")
async def search_knowledge_get(
    request: Request, q: str = "", collection: str = "", top_k: int = 5
):
    """Semantic search — searches all collections if none specified."""
    lt_memory = _get_ltm(request)
    if q == "__stats__":
        return {"stats": lt_memory.get_stats()}
    if collection:
        results = lt_memory.search(collection, q, top_k)
    else:
        results = lt_memory.search_all(q, top_k)
    return {"docs": results, "count": len(results)}


# ── Multipart file upload ──

@router.post("/api/knowledge/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    collection: str = Form(default="enterprise_wiki"),
):
    """Upload a file to the knowledge base. Supports .md, .txt, .html, .pdf."""
    try:
        raw = await file.read()
        filename = file.filename or "unknown"

        # PDF: extract text
        if filename.lower().endswith(".pdf"):
            text = _extract_pdf_text(raw, filename)
        else:
            text = raw.decode("utf-8")

        lt_memory = _get_ltm(request)

        if _dedup_check(lt_memory, collection, text):
            return {"filename": filename, "collection": collection, "chunks": 0,
                    "status": "duplicate", "message": "内容已存在，跳过重复录入"}

        meta = {"filename": filename, "source": "manual_upload", "content_hash": _content_hash(text)}
        chunks = lt_memory.ingest_document(collection, text, meta)
        return {"filename": filename, "collection": collection, "chunks": chunks, "status": "ok"}
    except Exception as e:
        logger.error("upload_error", error=str(e))
        return {"error": str(e)}, 500


# ── CRUD ──

@router.delete("/api/knowledge/{doc_id}")
async def delete_document(request: Request, doc_id: str, collection: str = "enterprise_wiki"):
    """Delete a document from the knowledge base."""
    try:
        lt_memory = _get_ltm(request)
        ok = lt_memory.delete_document(collection, doc_id)
        return {"deleted": ok, "doc_id": doc_id}
    except Exception as e:
        logger.error("delete_error", error=str(e))
        return {"error": str(e)}, 500


@router.get("/api/knowledge/stats")
async def knowledge_stats(request: Request):
    """Get knowledge base statistics."""
    try:
        lt_memory = _get_ltm(request)
        return {"stats": lt_memory.get_stats()}
    except Exception as e:
        logger.error("stats_error", error=str(e))
        return {"error": str(e)}, 500
