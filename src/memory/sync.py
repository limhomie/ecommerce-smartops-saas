"""DocumentSync with batch ingest — merges files before calling embedding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.observability.logger import get_logger

logger = get_logger(__name__)
BATCH_SIZE = 100  # files per add_documents call


def _hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


def _process_file(fpath: Path, db: dict, collection: str, stats: dict, ltm: Any, syncer: Any) -> None:
    """Process one file: check mtime → hash → skip/re-ingest."""
    key = str(fpath.resolve())
    old = db.get(key)
    current_mtime = fpath.stat().st_mtime
    if old and old.get("mtime") == current_mtime and old.get("hash"):
        stats["unchanged"] += 1
        return
    content = fpath.read_text(encoding="utf-8")
    h = _hash(content)
    if old and old["hash"] == h:
        db[key]["mtime"] = current_mtime
        stats["unchanged"] += 1
        return
    if old:
        syncer._delete_by_doc_id(key, collection)
    meta = {"source_doc_id": key, "filename": fpath.name, "content_hash": h}
    ltm.ingest_document(collection, content, meta)
    db[key] = {"hash": h, "mtime": current_mtime, "filename": fpath.name}
    stats["updated" if old else "created"] += 1


class DocumentSync:
    """Tracks files and syncs them to a ChromaDB collection in batches."""

    def __init__(self, long_term_memory: Any, registry_path: str = "data/doc_registry.json"):
        self.ltm = long_term_memory
        self._reg_path = Path(registry_path)
        self._db: dict[str, dict] = {}
        self._load()

    def sync_directory(self, dir_path: str, collection: str) -> dict[str, int]:
        d = Path(dir_path)
        if not d.exists():
            return {"error": f"not found: {dir_path}"}

        stats = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0}

        # Collect changed files (skip unchanged)
        changed: list[tuple[Path, str, str]] = []  # (path, content, hash)
        def _process(ext: str) -> None:
            for fpath in sorted(d.rglob(ext)):
                key = str(fpath.resolve())
                old = self._db.get(key)
                current_mtime = fpath.stat().st_mtime
                # mtime screening: skip unchanged files without reading content
                if old and old.get("mtime") == current_mtime and old.get("hash"):
                    stats["unchanged"] += 1
                    continue
                # mtime changed → read + compute hash to confirm
                content = fpath.read_text(encoding="utf-8")
                h = _hash(content)
                if old and old["hash"] == h:
                    # mtime changed but content hasn't (e.g. `touch` cmd)
                    self._db[key]["mtime"] = current_mtime
                    stats["unchanged"] += 1
                    continue
                changed.append((fpath, content, h))

        _process("*.md")
        _process("*.txt")

        # Ingest changed files (each goes through _chunk_text)
        for i in range(0, len(changed), BATCH_SIZE):
            batch = changed[i:i + BATCH_SIZE]
            for fpath, content, h in batch:
                key = str(fpath.resolve())
                old = self._db.get(key)
                if old:
                    self._delete_by_doc_id(key, collection)
                meta = {"source_doc_id": key, "filename": fpath.name, "content_hash": h}
                n = self.ltm.ingest_document(collection, content, meta)
                mtime = fpath.stat().st_mtime
                self._db[key] = {"hash": h, "mtime": mtime, "filename": fpath.name}
                stats["updated" if old else "created"] += 1
            logger.info("batch_ingested", count=len(batch), collection=collection)

        # Detect deletions
        prefix = str(d.resolve())
        for key in list(self._db):
            if key.startswith(prefix) and not Path(key).exists():
                self._db.pop(key, None)
                self._delete_by_doc_id(key, collection)
                stats["deleted"] += 1

        self._save()
        logger.info("sync_done", **stats)
        return stats

    def sync_file(self, file_path: str, collection: str) -> dict:
        """Sync a single file. Returns {created/updated/deleted/unchanged: 1}."""
        stats: dict[str, int] = {"created": 0, "updated": 0, "unchanged": 0}
        d = Path(file_path)
        if not d.exists():
            key = str(d.resolve())
            self._delete_by_doc_id(key, collection)
            self._db.pop(key, None)
            self._save()
            return {"deleted": 1}
        _process_file(d, self._db, collection, stats, self.ltm, self)
        self._save()
        return stats

    def _delete_by_doc_id(self, doc_id: str, collection: str) -> None:
        try:
            coll = self.ltm.store.get_or_create_collection(collection)
            coll.delete(where={"source_doc_id": doc_id})
        except Exception:
            pass

    def _load(self) -> None:
        self._reg_path.parent.mkdir(parents=True, exist_ok=True)
        if self._reg_path.exists():
            try:
                self._db = json.loads(self._reg_path.read_text(encoding="utf-8"))
            except Exception:
                self._db = {}

    def _save(self) -> None:
        self._reg_path.write_text(json.dumps(self._db, ensure_ascii=False, indent=2), encoding="utf-8")
