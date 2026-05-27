"""FreeAssist — Monitoring routes (drift detection, alerts)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_stats_service
from app.services.stats_service import StatsService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/alerts")
async def get_alerts(svc: Annotated[StatsService, Depends(get_stats_service)]) -> list[dict]:
    return svc.get_alerts()


@router.get("/drift")
async def get_drift(
    svc: Annotated[StatsService, Depends(get_stats_service)],
    top_intents: int = 3,
) -> list[dict]:
    return svc.get_drift_7days(top_intents=top_intents)
