"""Long-term knowledge base backed by ChromaDB.

Handles document ingestion, chunking, and semantic search for the enterprise Wiki.
"""

from __future__ import annotations

from pathlib import Path

from src.memory.vector_store import VectorStore
from src.observability.logger import get_logger

logger = get_logger(__name__)

# Collection names for different knowledge domains
COLLECTION_PRODUCTS = "products"
COLLECTION_COMPETITORS = "competitors"
COLLECTION_ADS = "ads_history"
COLLECTION_POLICIES = "policies"
COLLECTION_WIKI = "enterprise_wiki"


class LongTermMemory:
    """Long-term knowledge base using ChromaDB collections."""

    def __init__(self, vector_store: VectorStore, user_id: str = ""):
        self.store = vector_store
        self.user_id = user_id

    # ── Document ingestion ──

    def ingest_document(
        self, collection_name: str, content: str, metadata: dict | None = None
    ) -> int:
        """Chunk and ingest a document. Returns number of chunks created."""
        chunks = self._chunk_text(content)
        if not chunks:
            return 0
        metadatas = [metadata or {}] * len(chunks)
        self.store.add_documents(collection_name, chunks, metadatas, user_id=self.user_id)
        return len(chunks)

    def ingest_file(self, collection_name: str, file_path: str | Path) -> int:
        """Read a file and ingest its content."""
        path = Path(file_path)
        if not path.exists():
            logger.warning("file_not_found", path=str(path))
            return 0

        content = path.read_text(encoding="utf-8")
        return self.ingest_document(
            collection_name, content, {"source": str(path), "filename": path.name}
        )

    def ingest_directory(
        self, collection_name: str, dir_path: str | Path
    ) -> int:
        """Ingest all .md and .txt files from a directory."""
        path = Path(dir_path)
        total = 0
        for f in path.glob("*.md"):
            total += self.ingest_file(collection_name, f)
        for f in path.glob("*.txt"):
            total += self.ingest_file(collection_name, f)
        logger.info("directory_ingested", dir=str(path), chunks=total)
        return total

    # ── Search ──

    # Threshold: cosine distance > this means "not relevant"
    MAX_RELEVANCE_DISTANCE = 1.1

    def search(
        self, collection_name: str, query: str, top_k: int = 5,
        threshold: float | None = None,
    ) -> list[dict]:
        """Semantic search within a collection.

        Args:
            threshold: Max cosine distance for relevance. Docs with distance
                       above this are excluded. Defaults to MAX_RELEVANCE_DISTANCE.
        """
        threshold = threshold if threshold is not None else self.MAX_RELEVANCE_DISTANCE
        docs = self.store.search(
            collection_name, query, top_k=top_k, user_id=self.user_id
        )
        return [d for d in docs if d.get("distance", 0) <= threshold]

    def search_all(self, query: str, top_k: int = 5) -> list[dict]:
        """Search across all collections with diverse sampling.

        Each collection contributes its top-2 matches. Results are merged
        and ranked globally. This prevents one large collection (e.g. FAQ)
        from dominating the results.
        """
        per_coll = 3
        all_docs: list[dict] = []
        for coll in self.store.list_collections(user_id=self.user_id):
            docs = self.search(coll, query, top_k=per_coll)
            all_docs.extend(docs)
        all_docs.sort(key=lambda d: d.get("distance", 999))
        return all_docs[:top_k]

    # ── Wiki Q&A ──

    def wiki_search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search the enterprise wiki collection."""
        return self.search(COLLECTION_WIKI, query, top_k=top_k)

    def product_search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search the product knowledge base."""
        return self.search(COLLECTION_PRODUCTS, query, top_k=top_k)

    # ── CRUD ──

    def delete_document(self, collection_name: str, doc_id: str) -> bool:
        """Delete a document by ID. Returns True if successful."""
        try:
            collection = self.store.get_or_create_collection(
                collection_name, user_id=self.user_id
            )
            collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    def get_stats(self) -> dict:
        """Return document counts per collection."""
        return {
            name: self.store.count(name, user_id=self.user_id)
            for name in self.store.list_collections(user_id=self.user_id)
        }

    # ── Internal chunking ──

    def _chunk_text(self, text: str) -> list[str]:
        from config.settings import Settings

        settings = Settings()
        chunk_size = settings.chunk_size
        chunk_overlap = settings.chunk_overlap

        paragraphs = text.split("\n\n")
        chunks = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) <= chunk_size:
                current = (current + "\n\n" + para).strip()
            else:
                if current:
                    chunks.append(current)
                if len(para) > chunk_size:
                    words = para
                    for i in range(0, len(words), chunk_size - chunk_overlap):
                        chunk = words[i:i + chunk_size]
                        if chunk.strip():
                            chunks.append(chunk.strip())
                    current = ""
                else:
                    current = para

        if current:
            chunks.append(current)

        # Deduplicate exact matches (e.g. sliding window on repetitive content)
        chunks = list(dict.fromkeys(chunks))
        return chunks if chunks else [text]
