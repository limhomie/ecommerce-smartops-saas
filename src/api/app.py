"""FastAPI application factory for E-Commerce SmartOps Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from src.observability.logger import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initialize services on startup."""
    logger = get_logger(__name__)
    settings: Settings = app.state.settings
    logger.info("starting", environment=settings.environment)

    # Initialize LLM provider
    from src.llm import set_llm
    try:
        from src.llm.factory import create_llm_from_settings

        llm = create_llm_from_settings(settings)
        set_llm(llm)
        app.state.llm_provider = llm
        logger.info("llm_initialized", provider=settings.llm_provider)
    except Exception as e:
        logger.warning("llm_init_failed", error=str(e))
        from src.llm.mock import MockProvider

        llm = MockProvider()
        set_llm(llm)
        app.state.llm_provider = llm
        logger.info("llm_fallback_mock")

    # Initialize agent graph
    from src.agent.graph import build_graph

    app.state.agent_graph = build_graph(max_steps=settings.max_agent_steps)
    logger.info("agent_graph_initialized")

    # Initialize Redis + conversation memory
    try:
        from redis.asyncio import Redis

        from src.memory.short_term import RedisBackend, ShortTermMemory
        from src.memory.manager import MemoryManager

        app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await app.state.redis.ping()
        backend = RedisBackend(app.state.redis, tenant_id="default", ttl_seconds=3600)
        st_memory = ShortTermMemory(backend, window_size=settings.conversation_window_size)

        from src.memory.vector_store import VectorStore
        from src.memory.long_term import LongTermMemory

        vector_store = VectorStore(settings)
        lt_memory = LongTermMemory(vector_store)
        app.state.memory_manager = MemoryManager(st_memory, lt_memory, settings.conversation_window_size)
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))
        app.state.memory_manager = MemoryManager.create_default()
        logger.info("memory_fallback_in_memory")

    # Auto-ingest seed documents
    _ingest_seed_docs(app, settings, logger)

    yield

    if hasattr(app.state, "redis"):
        await app.state.redis.close()
    logger.info("shutdown")


def _ingest_seed_docs(app, settings, logger) -> None:
    """Ingest seed documents from data/documents/ into the knowledge base."""
    from pathlib import Path
    from config.settings import ROOT_DIR

    docs_dir = ROOT_DIR / "data" / "documents" / "products"
    if docs_dir.exists():
        try:
            from src.memory.long_term import LongTermMemory
            from src.memory.vector_store import VectorStore

            store = VectorStore(settings)
            lt = LongTermMemory(store)
            for coll in ["products", "enterprise_wiki"]:
                coll_dir = ROOT_DIR / "data" / "documents" / coll
                if coll_dir.exists():
                    lt.ingest_directory(coll, coll_dir)
            logger.info("seed_docs_ingested")
        except Exception as e:
            logger.warning("seed_ingest_failed", error=str(e))


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return the FastAPI application instance."""
    if settings is None:
        settings = Settings()

    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.state.settings = settings

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Observability
    from src.observability.middleware import ObservabilityMiddleware

    app.add_middleware(ObservabilityMiddleware)

    # Security
    from src.api.middleware import SecurityMiddleware

    app.add_middleware(SecurityMiddleware)

    # Exception handlers
    from src.api.exceptions import register_exception_handlers

    register_exception_handlers(app)

    # Routers
    from src.api.routers import health, chat, agent, knowledge, analytics

    app.include_router(health.router, tags=["health"])
    app.include_router(chat.router, tags=["chat"])
    app.include_router(agent.router, tags=["agent"])
    app.include_router(knowledge.router, tags=["knowledge"])
    app.include_router(analytics.router, tags=["analytics"])

    return app
