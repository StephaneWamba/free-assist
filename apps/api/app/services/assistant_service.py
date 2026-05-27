from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

from app.core.logging import get_logger
from app.services.intent_types import IntentPrediction
from app.services.stats_service import StatsService

logger = get_logger(__name__)


@dataclass
class AssistantResponse:
    intent: IntentPrediction
    suggested_response: str
    source_documents: list[str]
    summary: Optional[str]
    processing_ms: int
    cleaned_input: str


class AssistantService:
    def __init__(
        self,
        classifier: Any,
        rag: Any,
        stats: StatsService,
        summarizer: Any = None,
    ) -> None:
        self._classifier = classifier
        self._rag = rag
        self._stats = stats
        self._summarizer = summarizer

    def analyze(self, raw_text: str) -> AssistantResponse:
        t0 = time.perf_counter()

        from ml.utils.preprocessing import preprocess
        processed = preprocess(raw_text, anonymize_pii=True)
        clean_text = processed.cleaned
        logger.debug("Preprocessing done", pii_entities=processed.pii_entities)

        intent = self._classifier.predict(clean_text)
        logger.info("Intent classified", intent=intent.intent, confidence=intent.confidence)

        rag_result = self._rag.generate(clean_text, intent=intent.intent)

        summary: Optional[str] = None
        if len(raw_text.split()) > 80 and self._summarizer is not None:
            summary_result = self._summarizer(
                raw_text, max_length=60, min_length=20, do_sample=False
            )
            summary = summary_result[0]["summary_text"]

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        logger.info("Analysis complete", elapsed_ms=elapsed_ms)

        self._stats.record(
            intent=intent.intent,
            confidence=intent.confidence,
            processing_ms=elapsed_ms,
            text_preview=clean_text[:120],
        )

        return AssistantResponse(
            intent=intent,
            suggested_response=rag_result.answer,
            source_documents=rag_result.source_documents,
            summary=summary,
            processing_ms=elapsed_ms,
            cleaned_input=clean_text,
        )
