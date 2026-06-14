"""Memory Manager — coordinates short-term (Redis) and long-term (ChromaDB) memory."""

from __future__ import annotations

from src.memory.vector_store import VectorStore
from src.memory.short_term import ShortTermMemory, InMemoryBackend
from src.memory.long_term import LongTermMemory
from src.observability.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """Unified memory interface for agents."""

    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        window_size: int = 5,
    ):
        self.short_term = short_term
        self.long_term = long_term
        self.window_size = window_size

    @classmethod
    def create_default(cls) -> MemoryManager:
        """Create a MemoryManager with in-memory backend (no Redis/ChromaDB needed)."""
        backend = InMemoryBackend()
        short_term = ShortTermMemory(backend, window_size=5)
        from config.settings import Settings
        vector_store = VectorStore(Settings())
        long_term = LongTermMemory(vector_store)
        return cls(short_term, long_term)

    async def remember(self, session_id: str, role: str, content: str) -> None:
        """Store a message in short-term memory."""
        await self.short_term.add_message(session_id, role, content)

    async def recall(self, session_id: str) -> list[dict]:
        """Retrieve recent conversation context."""
        return await self.short_term.get_context(session_id)

    def search_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        """Search long-term knowledge base."""
        return self.long_term.product_search(query, top_k=top_k)

    def search_wiki(self, query: str, top_k: int = 5) -> list[dict]:
        """Search enterprise wiki."""
        return self.long_term.wiki_search(query, top_k=top_k)

    async def build_context(
        self, session_id: str, system_prompt: str, query: str
    ) -> tuple[list[dict], list[dict]]:
        """Build full context: conversation history + retrieved knowledge.

        Returns (messages_for_llm, retrieved_docs).
        """
        docs = self.search_knowledge(query)
        messages = await self.short_term.build_messages(session_id, system_prompt)

        if docs:
            knowledge = "\n".join(
                f"[来源 {i+1}] {d['content']}" for i, d in enumerate(docs)
            )
            messages.append({
                "role": "system",
                "content": f"以下是从知识库检索到的相关信息：\n{knowledge}",
            })

        return messages, docs
