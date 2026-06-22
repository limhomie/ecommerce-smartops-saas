"""CLI entry point for DocumentSync. Run directly on the host machine.

Usage:
    python scripts/sync_knowledge.py                          # sync all collections
    python scripts/sync_knowledge.py --collection products     # single collection
    python scripts/sync_knowledge.py --dry-run                 # show what would change
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from src.memory.long_term import LongTermMemory
from src.memory.sync import DocumentSync
from src.memory.vector_store import VectorStore

COLLECTIONS: dict[str, str] = {
    "products": "data/documents/products",
    "policies": "data/documents/policies",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync knowledge base documents")
    parser.add_argument("--collection", "-c", help="Only sync one collection")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without syncing")
    args = parser.parse_args()

    s = Settings()
    store = VectorStore(s)
    ltm = LongTermMemory(store)

    jobs = {args.collection: COLLECTIONS[args.collection]} if args.collection else COLLECTIONS

    for coll_name, dir_path in jobs.items():
        d = Path(dir_path)
        if not d.exists():
            print(f"[{coll_name}] SKIP: directory not found")
            continue

        if args.dry_run:
            file_count = len(list(d.rglob("*.md")))
            print(f"[{coll_name}] DRY-RUN: {file_count} files in {dir_path}")
            continue

        sync = DocumentSync(ltm)
        result = sync.sync_directory(dir_path, coll_name)
        print(f"[{coll_name}] synced: {result}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
