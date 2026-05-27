"""FreeAssist — Assistant REST + WebSocket routes."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.core.logging import get_logger
from app.schemas.assistant import AnalyzeRequest, AnalyzeResponse
from app.services.assistant_service import AssistantService
from app.api.v1.dependencies import get_assistant_service

logger = get_logger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze_ticket(
    request: AnalyzeRequest,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AnalyzeResponse:
    """
    Analyze a support ticket:
    - Classify intent
    - Generate a suggested response via RAG
    - Optionally summarize long tickets
    """
    try:
        result = service.analyze(request.text)
    except Exception as exc:
        logger.error("Analysis failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Analysis pipeline error") from exc

    return AnalyzeResponse(
        intent=result.intent.intent,
        confidence=result.intent.confidence,
        all_scores=result.intent.all_scores,  # type: ignore[arg-type]
        suggested_response=result.suggested_response,
        source_documents=result.source_documents,
        summary=result.summary,
        processing_ms=result.processing_ms,
        cleaned_input=result.cleaned_input,
    )


@router.websocket("/ws/{conversation_id}")
async def assistant_ws(websocket: WebSocket, conversation_id: str) -> None:
    """WebSocket: client sends {"text": "..."}, server responds with AnalyzeResponse JSON."""
    service: AssistantService | None = getattr(websocket.app.state, "assistant_service", None)
    if service is None:
        await websocket.close(code=1013)
        return

    await websocket.accept()
    logger.info("WebSocket connected", conversation_id=conversation_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                text = payload.get("text", "").strip()
            except (json.JSONDecodeError, AttributeError):
                await websocket.send_json({"error": "Invalid JSON payload"})
                continue

            if not text or len(text) < 3:
                continue

            try:
                result = service.analyze(text)
                await websocket.send_json({
                    "intent": result.intent.intent,
                    "confidence": result.intent.confidence,
                    "all_scores": result.intent.all_scores,
                    "suggested_response": result.suggested_response,
                    "source_documents": result.source_documents,
                    "summary": result.summary,
                    "processing_ms": result.processing_ms,
                })
            except Exception as exc:
                logger.error("WS analysis failed", error=str(exc))
                await websocket.send_json({"error": "Pipeline error"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", conversation_id=conversation_id)
