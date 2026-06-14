"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ecommerce-smartops-agent",
        "version": "0.1.0",
    }
