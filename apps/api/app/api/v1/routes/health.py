"""FreeAssist — Health check route."""

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    ml_mode: str
    classifier_loaded: bool
    rag_loaded: bool
    openai_status: str  # "ok" | "no_key" | "error"
    openai_model: str | None
    version: str = "0.1.0"


async def _check_openai(api_key: str | None) -> tuple[str, str | None]:
    if not api_key:
        return "no_key", None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if r.status_code == 200:
            return "ok", "gpt-4o-mini"
        return "error", None
    except Exception:
        return "error", None


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    service = getattr(request.app.state, "assistant_service", None)
    ml_mode = getattr(request.app.state, "ml_mode", "none")
    settings = get_settings()
    openai_status, openai_model = await _check_openai(settings.openai_api_key)
    return HealthResponse(
        status="ok" if service else "degraded",
        ml_mode=ml_mode,
        classifier_loaded=bool(service and service._classifier.is_loaded()),
        rag_loaded=bool(service and service._rag.is_loaded()),
        openai_status=openai_status,
        openai_model=openai_model,
    )
