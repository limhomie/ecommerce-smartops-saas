"""Agent-level query→response cache with two-stage lookup.

Stage 1 (exact): Normalize question text (strip stop words, sort keywords),
                  compute MD5 → O(1) lookup.  Zero extra latency.
Stage 2 (semantic): If exact miss, embed the question with BGE and compare
                    cosine similarity against all cached embeddings.
                    Falls back gracefully if the embedding model is unavailable.

Caches the final output (report, charts, action items) so repeat or
semantically-similar questions skip the entire Agent graph pipeline.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

from src.observability.logger import get_logger

logger = get_logger(__name__)

# ── Stop words stripped during text normalization (longest-first to
#    avoid partial matches, e.g. "帮我" before "我"). ──
_STOP_WORDS: list[str] = sorted(
    [
        "的", "了", "吗", "呢", "吧", "啊", "呀", "哦", "哈",
        "请", "帮我", "麻烦", "能不能", "可以", "帮我看看",
        "给", "为", "一个", "一下", "点", "些", "这个", "那个",
        "来", "去", "是", "有", "在", "和", "与", "或", "及",
        "哪种", "各种", "哪些",
        "怎么", "如何", "为什么", "多少", "哪个", "哪里",
        "需要", "要不要",
    ],
    key=len,
    reverse=True,
)


def normalize(text: str) -> str:
    """Remove stop words and punctuation so trivially-equivalent queries
    share the same MD5 key for Stage-1 exact-match lookup.

    Examples (Stage 1 — exact, same key):
        "帮我分析转化率" → "分析转化率"
        "竞品价格怎么分析呢" → "竞品价格分析"

    Order-different equivalents (Stage 2 — semantic via BGE):
        "生成有机棉T恤的Facebook广告脚本"
        "为有机棉T恤生成Facebook广告脚本吗"
    """
    text = text.strip().lower()
    # Remove punctuation (keep alphanum + Chinese + spaces)
    text = re.sub(r"[^\w一-鿿㐀-䶿]+", " ", text)
    # Remove stop words (replace with empty — Chinese has no word delimiters)
    for sw in _STOP_WORDS:
        text = text.replace(sw, "")
    # Collapse any remaining whitespace (from punctuation replacement)
    return re.sub(r"\s+", "", text).strip()


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


class AgentCache:
    """Two-stage query→response cache.

    Stage 1 — exact:  normalized MD5 hash, O(1), ~0 ms.
    Stage 2 — semantic: BGE embedding + cosine similarity, ~50 ms.
    """

    def __init__(
        self,
        ttl_seconds: int = 600,
        cache_file: str | None = None,
        semantic_threshold: float = 0.92,
        enable_semantic: bool = True,
    ):
        self.ttl = ttl_seconds
        self.semantic_threshold = semantic_threshold
        self._enable_semantic = enable_semantic

        # _store:  norm_hash → (timestamp, result_dict)
        self._store: dict[str, tuple[float, dict]] = {}
        # _embeddings:  [(norm_hash, embedding_vector), ...]
        self._embeddings: list[tuple[str, list[float]]] = []

        self._cache_file = cache_file
        self._embedding_fn = None  # lazy init

        # Hit-rate counters (not persisted — reset on restart)
        self._hits_exact: int = 0
        self._hits_semantic: int = 0
        self._misses: int = 0

        if self._cache_file:
            self._load()

    # ── Public API ──

    def get(self, question: str, user_id: str = "") -> dict | None:
        """Two-stage lookup. Returns cached result or None."""
        norm = normalize(question)
        key = self._hash_norm(user_id + ":" + norm if user_id else norm)

        # ── Stage 1: exact match ──
        entry = self._store.get(key)
        if entry is not None:
            ts, data = entry
            if time.time() - ts < self.ttl:
                self._hits_exact += 1
                logger.info("cache_hit_exact", question_preview=question[:80])
                return data
            # Expired — clean up
            del self._store[key]
            self._embeddings = [(k, e) for k, e in self._embeddings if k != key]
            self._save()

        # ── Stage 2: semantic match ──
        if self._enable_semantic and self._embeddings:
            result = self._semantic_search(question)  # use raw question for embedding
            if result is not None:
                return result

        self._misses += 1
        return None

    def set(self, question: str, result: dict, user_id: str = "") -> None:
        """Store a result, keyed by normalized question text."""
        norm = normalize(question)
        key = self._hash_norm(user_id + ":" + norm if user_id else norm)
        self._store[key] = (time.time(), result)

        # Also store embedding for future semantic searches
        if self._enable_semantic:
            self._store_embedding(key, question)  # embed raw question, not normalized

        self._save()
        logger.info("cache_write", question_preview=question[:80])

    def clear(self) -> None:
        self._store.clear()
        self._embeddings.clear()
        self._save()

    def stats(self) -> dict:
        total = len(self._store)
        active = sum(1 for ts, _ in self._store.values() if time.time() - ts < self.ttl)
        total_lookups = self._hits_exact + self._hits_semantic + self._misses
        hit_rate = (
            round((self._hits_exact + self._hits_semantic) / total_lookups * 100, 1)
            if total_lookups > 0
            else 0
        )
        return {
            "entries_total": total,
            "entries_active": active,
            "embeddings": len(self._embeddings),
            "ttl_seconds": self.ttl,
            "hits_exact": self._hits_exact,
            "hits_semantic": self._hits_semantic,
            "misses": self._misses,
            "hit_rate_pct": hit_rate,
            "semantic_enabled": self._enable_semantic and self._embedding_fn is not None,
            "semantic_threshold": self.semantic_threshold,
        }

    # ── Semantic search ──

    def _semantic_search(self, raw_question: str) -> dict | None:
        """Find the closest cached question by cosine similarity."""
        embedding_fn = self._get_embedding_fn()
        if embedding_fn is None:
            return None

        try:
            query_vec = embedding_fn.encode(
                [raw_question], show_progress_bar=False
            )[0].tolist()
        except Exception as e:
            logger.warning("semantic_embed_failed", error=str(e))
            return None

        best_key: str | None = None
        best_sim: float = -1.0

        for key, emb in self._embeddings:
            sim = _cosine_sim(query_vec, emb)
            if sim > best_sim:
                best_sim = sim
                best_key = key

        if best_sim < self.semantic_threshold or best_key is None:
            return None

        entry = self._store.get(best_key)
        if entry is None:
            return None

        ts, data = entry
        if time.time() - ts >= self.ttl:
            del self._store[best_key]
            self._embeddings = [(k, e) for k, e in self._embeddings if k != best_key]
            self._save()
            return None

        self._hits_semantic += 1
        logger.info(
            "cache_hit_semantic",
            question_preview=raw_question[:80],
            similarity=round(best_sim, 4),
        )
        return data

    def _store_embedding(self, key: str, raw_question: str) -> None:
        embedding_fn = self._get_embedding_fn()
        if embedding_fn is None:
            return
        # Don't store duplicate embeddings for the same key
        if any(k == key for k, _ in self._embeddings):
            return
        try:
            vec = embedding_fn.encode(
                [raw_question], show_progress_bar=False
            )[0].tolist()
            self._embeddings.append((key, vec))
        except Exception as e:
            logger.warning("embedding_store_failed", error=str(e))

    def _get_embedding_fn(self):
        if self._embedding_fn is not None:
            return self._embedding_fn
        try:
            import sentence_transformers

            from config.settings import Settings

            s = Settings()
            # Try local-only first (instant if cached, no HF network).
            for local_only in (True, False):
                try:
                    self._embedding_fn = sentence_transformers.SentenceTransformer(
                        s.embedding_model,
                        device=s.embedding_device,
                        local_files_only=local_only,
                    )
                    break
                except Exception:
                    if not local_only:
                        raise

            self._embedding_fn.encode(["warmup"], show_progress_bar=False)[0].tolist()  # noqa
            logger.info("semantic_cache_ready", model=s.embedding_model)
        except Exception as e:
            logger.warning("semantic_cache_unavailable", error=str(e))
            self._enable_semantic = False
            self._embedding_fn = None
        return self._embedding_fn

    # ── Hashing ──

    @staticmethod
    def _hash_norm(normalized: str) -> str:
        return hashlib.md5(normalized.encode()).hexdigest()

    # ── Persistence ──

    def _save(self) -> None:
        if not self._cache_file:
            return
        try:
            data = {
                "store": {k: [ts, v] for k, (ts, v) in self._store.items()},
                "embeddings": [[k, e] for k, e in self._embeddings],
            }
            path = Path(self._cache_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning("cache_save_failed", error=str(e))

    def _load(self) -> None:
        try:
            path = Path(self._cache_file)
            if not path.exists():
                return
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self._store = {
                k: (float(ts), v) for k, [ts, v] in data.get("store", {}).items()
            }
            self._embeddings = [
                (k, [float(x) for x in e])
                for k, e in data.get("embeddings", [])
            ]
            logger.info(
                "cache_loaded",
                entries=len(self._store),
                embeddings=len(self._embeddings),
            )
        except Exception as e:
            logger.warning("cache_load_failed", error=str(e))
            self._store = {}
            self._embeddings = []


# Module-level singleton
_agent_cache: AgentCache | None = None


def get_agent_cache() -> AgentCache:
    global _agent_cache
    if _agent_cache is None:
        from config.settings import Settings, ROOT_DIR

        s = Settings()
        ttl = getattr(s, "agent_cache_ttl", 600)
        threshold = getattr(s, "agent_cache_semantic_threshold", 0.92)
        cache_path = str(ROOT_DIR / "data" / "agent_cache.json")
        _agent_cache = AgentCache(
            ttl_seconds=ttl,
            cache_file=cache_path,
            semantic_threshold=threshold,
            enable_semantic=True,
        )
    return _agent_cache
