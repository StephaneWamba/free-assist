"""
FreeAssist — Remote Inference Client

Calls the Vast.ai inference server (CamemBERT + RAG).
Same interface as IntentClassifier + OpenAIRAGService so AssistantService needs zero changes.
Falls back transparently when the server is unreachable.
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.services.intent_types import IntentPrediction

logger = get_logger(__name__)

INTENTS = [
    "BOX_CONNECTIVITY", "BOX_REBOOT", "MOBILE_PORTABILITY",
    "BILLING_DISPUTE", "CONTRACT_CHANGE", "TECHNICAL_OUTAGE",
    "EQUIPMENT_RETURN", "SPEED_ISSUE", "CANCELLATION", "OTHER",
]


class RemoteInferenceResult:
    def __init__(self, answer: str, sources: list[str]) -> None:
        self.answer = answer
        self.source_documents = sources


class RemoteClassifier:
    """Calls /predict on the Vast.ai inference server."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._loaded = False

    def load(self) -> None:
        try:
            r = httpx.get(f"{self._base_url}/health", timeout=5.0)
            if r.status_code == 200:
                self._loaded = True
                logger.info("Remote inference server reachable", url=self._base_url)
            else:
                logger.warning("Inference server unhealthy", status=r.status_code)
        except Exception as e:
            logger.warning("Inference server unreachable", error=str(e))

    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, text: str) -> IntentPrediction:
        r = httpx.post(
            f"{self._base_url}/predict",
            json={"text": text},
            timeout=self._timeout,
        )
        r.raise_for_status()
        data = r.json()
        return IntentPrediction(
            intent=data["intent"],
            confidence=data["confidence"],
            all_scores=data.get("all_scores", {i: 0.0 for i in INTENTS}),
        )


class RemoteRAGService:
    """Calls /generate on the Vast.ai inference server."""

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._loaded = True

    def load(self) -> None:
        pass

    def is_loaded(self) -> bool:
        return True

    def generate(self, text: str, intent: str = "OTHER") -> RemoteInferenceResult:
        r = httpx.post(
            f"{self._base_url}/generate",
            json={"text": text, "intent": intent},
            timeout=self._timeout,
        )
        r.raise_for_status()
        data = r.json()
        return RemoteInferenceResult(
            answer=data["answer"],
            sources=data.get("sources", []),
        )
