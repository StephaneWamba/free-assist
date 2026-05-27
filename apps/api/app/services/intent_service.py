"""
FreeAssist — Intent Classification Service

Wraps the fine-tuned CamemBERT model with caching and fallback logic.
Single instance loaded at startup via FastAPI lifespan.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.services.intent_types import INTENTS, IntentPrediction

logger = get_logger(__name__)


class IntentClassifier:
    def __init__(self, model_path: str, device: str = "cpu") -> None:
        self._model_path = model_path
        self._device = device
        self._pipeline = None

    def load(self) -> None:
        import torch
        from transformers import pipeline
        logger.info("Loading intent classifier", model_path=self._model_path)
        self._pipeline = pipeline(
            task="text-classification",
            model=self._model_path,
            tokenizer=self._model_path,
            device=0 if self._device == "cuda" and torch.cuda.is_available() else -1,
            top_k=None,
            truncation=True,
            max_length=128,
        )
        logger.info("Intent classifier loaded")

    def predict(self, text: str) -> IntentPrediction:
        if self._pipeline is None:
            raise RuntimeError("Classifier not loaded. Call load() first.")

        results: list[dict] = self._pipeline(text)[0]  # type: ignore[index]
        all_scores = {r["label"]: round(r["score"], 4) for r in results}
        top = max(results, key=lambda r: r["score"])

        return IntentPrediction(
            intent=top["label"],
            confidence=round(top["score"], 4),
            all_scores=all_scores,
        )

    def is_loaded(self) -> bool:
        return self._pipeline is not None
