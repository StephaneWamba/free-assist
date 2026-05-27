"""Shared intent types — no heavy ML dependencies."""

from __future__ import annotations

from dataclasses import dataclass

INTENTS = [
    "BOX_CONNECTIVITY", "BOX_REBOOT", "MOBILE_PORTABILITY",
    "BILLING_DISPUTE", "CONTRACT_CHANGE", "TECHNICAL_OUTAGE",
    "EQUIPMENT_RETURN", "SPEED_ISSUE", "CANCELLATION", "OTHER",
]


@dataclass(frozen=True)
class IntentPrediction:
    intent: str
    confidence: float
    all_scores: dict[str, float]
