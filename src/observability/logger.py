"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import structlog

from config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structlog with environment-appropriate settings."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
        if settings.debug
        else structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "chromadb", "sentence_transformers"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str | None = None):
    """Return a structlog logger bound with module name."""
    return structlog.get_logger(name or __name__)
