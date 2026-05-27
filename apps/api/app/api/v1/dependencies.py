"""FastAPI dependency injection — services resolved from app state."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.services.assistant_service import AssistantService
from app.services.stats_service import StatsService


def get_assistant_service(request: Request) -> AssistantService:
    svc = getattr(request.app.state, "assistant_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="AssistantService unavailable — check logs")
    return svc


def get_stats_service(request: Request) -> StatsService:
    svc = getattr(request.app.state, "stats_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="StatsService unavailable")
    return svc
