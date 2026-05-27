"""
FreeAssist — Experiments routes

Proxies MLflow REST API for the frontend dashboard.
Avoids exposing MLflow directly to the browser.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings

router = APIRouter(prefix="/experiments", tags=["experiments"])
settings = get_settings()


async def _mlflow_get(path: str, params: dict | None = None) -> dict:
    url = f"{settings.mlflow_tracking_uri}/api/2.0/mlflow/{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params or {})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="MLflow unreachable")
    return resp.json()


@router.get("")
async def list_experiments():
    return await _mlflow_get("experiments/search", {"max_results": 50})


@router.get("/{experiment_id}/runs")
async def list_runs(experiment_id: str, max_results: int = Query(50, le=200)):
    return await _mlflow_get(
        "runs/search",
        {"experiment_ids": f'["{experiment_id}"]', "max_results": max_results},
    )


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    return await _mlflow_get("runs/get", {"run_id": run_id})


@router.get("/runs/{run_id}/metrics")
async def get_metrics(run_id: str, metric_key: str = Query(...)):
    return await _mlflow_get(
        "metrics/get-history",
        {"run_id": run_id, "metric_key": metric_key},
    )
