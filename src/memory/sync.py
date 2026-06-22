"""DocumentSync — incremental knowledge base update pipeline.

Detects file changes (new / modified / deleted) via content hash +
last-modified time.  Deletes old chunks by source_doc_id metadata,
re-chunks changed files, and skips unchanged ones.

Usage:
    from src.memory.sync import DocumentSync
    sync = DocumentSync(long_term_memory)
    result = sync.sync_directory("data/documents/products", "products")
    # → {created: 5000, updated: 12, deleted: 3, unchanged: 4985}
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.observability.logger import get_logger

logger = get_logger(__name__)


def _hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


class DocumentSync:
    """Tracks files and syncs them to a ChromaDB collection."""

    def __init__(self, long_term_memory: Any, registry_path: str = "data/doc_registry.json"):
        self.ltm = long_term_memory
        self._reg_path = Path(registry_path)
        self._db: dict[str, dict] = {}  # abs_path → {hash, mtime, filename}
        self._load()

    # ── Public ──

    def sync_directory(self, dir_path: str, collection: str) -> dict[str, int]:
        """Sync all .md/.txt files under dir_path to a collection."""
        d = Path(dir_path)
        if not d.exists():
            return {"error": f"not found: {dir_path}"}

        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0}

        # 1️⃣ Process existing files
        for fpath in sorted(d.rglob("*.md")):
            self._sync_one(fpath, collection, stats)
        for fpath in sorted(d.rglob("*.txt")):
            self._sync_one(fpath, collection, stats)

        # 2️⃣ Detect deleted files
        prefix = str(d.resolve())
        for key in list(self._db):
            if key.startswith(prefix) and not Path(key).exists():
                self._on_deleted(key, collection, stats)

        self._save()
        logger.info("sync_done", **stats)
        return stats

    def sync_file(self, file_path: str, collection: str) -> dict[str, int]:
        """Sync a single file.  Returns {created/updated/unchanged: 1} or {deleted: 1}."""
        stats: dict[str, int] = {}
        self._sync_one(Path(file_path), collection, stats)
        if not Path(file_path).exists():
            self._on_deleted(str(Path(file_path).resolve()), collection, stats)
        self._save()
        return stats

    # ── Internal ──

    def _sync_one(self, fpath: Path, collection: str, stats: dict[str, int]) -> None:
        key = str(fpath.resolve())
        mtime = fpath.stat().st_mtime
        content = fpath.read_text(encoding="utf-8")
        h = _hash(content)

        old = self._db.get(key)
        if old and old["hash"] == h:
            stats["unchanged"] += 1
            return

        # Delete old chunks
        if old:
            self._delete_by_doc_id(key, collection)

        # Re-ingest
        meta = {"source_doc_id": key, "filename": fpath.name, "content_hash": h}
        n = self.ltm.ingest_document(collection, content, meta)
        self._db[key] = {"hash": h, "mtime": mtime, "filename": fpath.name}
        stats["updated" if old else "created"] += 1

    def _on_deleted(self, key: str, collection: str, stats: dict[str, int]) -> None:
        self._db.pop(key, None)
        self._delete_by_doc_id(key, collection)
        stats["deleted"] += 1

    def _delete_by_doc_id(self, doc_id: str, collection: str) -> None:
        """Delete all chunks with this source_doc_id from the vector store."""
        try:
            coll = self.ltm.store.get_or_create_collection(collection)
            coll.delete(where={"source_doc_id": doc_id})
        except Exception:
            logger.warning("chunk_delete_failed", doc_id=doc_id)

    def _load(self) -> None:
        self._reg_path.parent.mkdir(parents=True, exist_ok=True)
        if self._reg_path.exists():
            try:
                self._db = json.loads(self._reg_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("registry_load_failed", error=str(e))
                self._db = {}

    def _save(self) -> None:
        self._reg_path.write_text(json.dumps(self._db, ensure_ascii=False, indent=2), encoding="utf-8")
