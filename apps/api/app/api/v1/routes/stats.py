"""FreeAssist — Stats routes (dashboard KPIs, recent tickets, intent distribution)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_stats_service
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/kpis")
async def get_kpis(svc: Annotated[StatsService, Depends(get_stats_service)]) -> dict:
    return svc.get_kpis()


@router.get("/recent")
async def get_recent(
    svc: Annotated[StatsService, Depends(get_stats_service)],
    limit: int = 10,
) -> list[dict]:
    return svc.get_recent(limit=min(limit, 50))


@router.get("/intent-distribution")
async def get_intent_distribution(
    svc: Annotated[StatsService, Depends(get_stats_service)],
) -> list[dict]:
    return svc.get_intent_distribution()
