"""ChromaDB vector store wrapper for document embedding and retrieval."""

from __future__ import annotations

import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import sys
import io
import logging

# Suppress chromadb telemetry noise during import (PostHog 7.x API incompatibility)
_stderr = sys.stderr
sys.stderr = io.StringIO()
import chromadb
from chromadb.config import Settings as ChromaSettings
sys.stderr = _stderr

# Suppress future telemetry errors
for _name in ("chromadb", "chromadb.telemetry.product.posthog", "posthog"):
    logging.getLogger(_name).setLevel(logging.CRITICAL)

from config.settings import Settings
from src.observability.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Wraps ChromaDB for embedding + retrieval operations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        persist_dir = settings.chroma_persist_dir
        if persist_dir.startswith("./"):
            from config.settings import ROOT_DIR
            persist_dir = str(ROOT_DIR / persist_dir[2:])

        if settings.chroma_mode == "embedded":
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host, port=settings.chroma_port
            )

        self._embedding_fn = None

    def _get_embedding_fn(self):
        if self._embedding_fn is None:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            self._embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=self.settings.embedding_model,
                device=self.settings.embedding_device,
            )
        return self._embedding_fn

    @staticmethod
    def _resolve_name(name: str, user_id: str) -> str:
        return f"user_{user_id}_{name}" if user_id else name

    def get_or_create_collection(
        self, name: str, user_id: str = ""
    ) -> chromadb.Collection:
        resolved = self._resolve_name(name, user_id)
        embed_fn = self._get_embedding_fn()
        return self._client.get_or_create_collection(
            name=resolved, embedding_function=embed_fn
        )

    def list_collections(self, user_id: str = "") -> list[str]:
        all_names = [c.name for c in self._client.list_collections()]
        if not user_id:
            return all_names
        prefix = f"user_{user_id}_"
        return [n[len(prefix) :] for n in all_names if n.startswith(prefix)]

    def delete_collection(self, name: str, user_id: str = "") -> None:
        try:
            self._client.delete_collection(self._resolve_name(name, user_id))
            logger.info("collection_deleted", name=name)
        except Exception:
            pass

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
        user_id: str = "",
    ) -> None:
        if not documents:
            return
        collection = self.get_or_create_collection(collection_name, user_id=user_id)
        if ids is None:
            import hashlib
            ids = []
            for i, doc in enumerate(documents):
                h = hashlib.md5(doc.encode()).hexdigest()[:12]
                src = metadatas[i].get("source", metadatas[i].get("filename", "")) if metadatas else ""
                prefix = f"{src}_{h}" if src else h
                ids.append(f"{prefix}_{i}")  # index suffix guarantees uniqueness
        try:
            collection.upsert(documents=documents, metadatas=metadatas or [{}]*len(documents), ids=ids)
        except AttributeError:
            collection.add(documents=documents, metadatas=metadatas or [{}]*len(documents), ids=ids)
        logger.info("documents_added", collection=collection_name, count=len(documents))

    def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        user_id: str = "",
    ) -> list[dict]:
        collection = self.get_or_create_collection(collection_name, user_id=user_id)
        results = collection.query(query_texts=[query], n_results=top_k)
        docs = []
        for i in range(len(results["documents"][0])):
            meta = dict(results["metadatas"][0][i]) if results["metadatas"] else {}
            meta.setdefault("collection", collection_name)
            docs.append({
                "content": results["documents"][0][i],
                "metadata": meta,
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
        return docs

    def count(self, collection_name: str, user_id: str = "") -> int:
        try:
            collection = self.get_or_create_collection(collection_name, user_id=user_id)
            return collection.count()
        except Exception:
            return 0
