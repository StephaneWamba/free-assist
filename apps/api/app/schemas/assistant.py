"""FreeAssist — Pydantic schemas for the assistant API."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=4000, description="Raw ticket text from the client")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for multi-turn context")


class IntentScores(BaseModel):
    BOX_CONNECTIVITY: float
    BOX_REBOOT: float
    MOBILE_PORTABILITY: float
    BILLING_DISPUTE: float
    CONTRACT_CHANGE: float
    TECHNICAL_OUTAGE: float
    EQUIPMENT_RETURN: float
    SPEED_ISSUE: float
    CANCELLATION: float
    OTHER: float


class AnalyzeResponse(BaseModel):
    intent: str
    confidence: float
    all_scores: IntentScores
    suggested_response: str
    source_documents: list[str]
    summary: Optional[str] = None
    processing_ms: int
    cleaned_input: str


class HealthResponse(BaseModel):
    status: str
    classifier_loaded: bool
    rag_loaded: bool
    version: str = "0.1.0"
