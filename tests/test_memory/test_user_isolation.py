"""Tests for user-scoped memory isolation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from config.settings import Settings
from src.memory.long_term import LongTermMemory
from src.memory.vector_store import VectorStore


@pytest.fixture
def settings():
    s = Settings()
    d = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    s.chroma_persist_dir = str(Path(d.name) / "chroma")
    yield s
    d.cleanup()


class TestUserIsolation:
    def test_different_users_dont_share_docs(self, settings):
        store = VectorStore(settings)

        ltm_a = LongTermMemory(store, user_id="user_a")
        ltm_a.ingest_document("products", "User A: organic cotton T-shirt $29.99", {"source": "test"})

        ltm_b = LongTermMemory(store, user_id="user_b")
        results = ltm_b.product_search("cotton T-shirt")
        assert len(results) == 0

    def test_same_user_finds_own_docs(self, settings):
        store = VectorStore(settings)

        ltm_a = LongTermMemory(store, user_id="user_c")
        ltm_a.ingest_document("products", "User C: bamboo socks breathable", {"source": "test"})

        results = ltm_a.product_search("bamboo socks")
        assert len(results) >= 1
        assert "bamboo" in results[0]["content"]

    def test_empty_user_id_backwards_compat(self, settings):
        store = VectorStore(settings)

        ltm = LongTermMemory(store, user_id="")
        ltm.ingest_document("products", "Shared: running shoes $89", {"source": "test"})

        results = ltm.product_search("running shoes")
        assert len(results) >= 1
