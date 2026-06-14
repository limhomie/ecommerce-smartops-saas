"""Knowledge base management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, UploadFile, File, Form
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


@router.post("/api/knowledge/search")
async def search_knowledge(request: Request, body: SearchRequest):
    """Semantic search across the knowledge base."""
    try:
        memory_manager = getattr(request.app.state, "memory_manager", None)
        if memory_manager is None:
            from src.memory.manager import MemoryManager
            memory_manager = MemoryManager.create_default()

        if body.collection == "enterprise_wiki":
            results = memory_manager.search_wiki(body.query, body.top_k)
        else:
            results = memory_manager.search_knowledge(body.query, body.top_k)

        return {"query": body.query, "results": results, "count": len(results)}
    except Exception as e:
        logger.error("search_error", error=str(e))
        return {"error": str(e)}, 500


@router.post("/api/knowledge/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    collection: str = Form(default="enterprise_wiki"),
):
    """Upload a document to the knowledge base."""
    try:
        content = await file.read()
        text = content.decode("utf-8")

        from src.memory.manager import MemoryManager
        from src.memory.long_term import LongTermMemory
        from src.memory.vector_store import VectorStore
        from config.settings import Settings

        settings: Settings = request.app.state.settings
        store = VectorStore(settings)
        lt_memory = LongTermMemory(store)
        chunks = lt_memory.ingest_document(collection, text, {"filename": file.filename})

        return {"filename": file.filename, "collection": collection, "chunks": chunks}
    except Exception as e:
        logger.error("upload_error", error=str(e))
        return {"error": str(e)}, 500


@router.delete("/api/knowledge/{doc_id}")
async def delete_document(request: Request, doc_id: str, collection: str = "enterprise_wiki"):
    """Delete a document from the knowledge base."""
    try:
        from src.memory.long_term import LongTermMemory
        from src.memory.vector_store import VectorStore
        from config.settings import Settings

        settings: Settings = request.app.state.settings
        store = VectorStore(settings)
        lt_memory = LongTermMemory(store)
        ok = lt_memory.delete_document(collection, doc_id)
        return {"deleted": ok, "doc_id": doc_id}
    except Exception as e:
        logger.error("delete_error", error=str(e))
        return {"error": str(e)}, 500


@router.get("/api/knowledge/stats")
async def knowledge_stats(request: Request):
    """Get knowledge base statistics."""
    try:
        from src.memory.long_term import LongTermMemory
        from src.memory.vector_store import VectorStore
        from config.settings import Settings

        settings: Settings = request.app.state.settings
        store = VectorStore(settings)
        lt_memory = LongTermMemory(store)
        return {"stats": lt_memory.get_stats()}
    except Exception as e:
        logger.error("stats_error", error=str(e))
        return {"error": str(e)}, 500
