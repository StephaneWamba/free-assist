"""
FreeAssist — OpenAI Fallback Services

Used when fine-tuned ML models are not yet downloaded on the volume.
Provides the same interface as IntentClassifier + FreeAssistRAG
so AssistantService needs zero changes.

Degradation chain:
  CamemBERT (local) → GPT-4o-mini (OpenAI) for intent
  Mistral-7B RAG    → GPT-4o (OpenAI) for generation
"""

from __future__ import annotations

import json
import time

from openai import OpenAI

from app.core.logging import get_logger
from app.services.intent_types import IntentPrediction

logger = get_logger(__name__)

INTENTS = [
    "BOX_CONNECTIVITY", "BOX_REBOOT", "MOBILE_PORTABILITY",
    "BILLING_DISPUTE", "CONTRACT_CHANGE", "TECHNICAL_OUTAGE",
    "EQUIPMENT_RETURN", "SPEED_ISSUE", "CANCELLATION", "OTHER",
]

INTENT_PROMPT = """\
Tu es un classificateur d'intentions pour le support technique de Free (opérateur télécom français).
Classifie le message client ci-dessous parmi ces intentions :
BOX_CONNECTIVITY, BOX_REBOOT, MOBILE_PORTABILITY, BILLING_DISPUTE, CONTRACT_CHANGE,
TECHNICAL_OUTAGE, EQUIPMENT_RETURN, SPEED_ISSUE, CANCELLATION, OTHER

Réponds UNIQUEMENT en JSON avec ces clés :
{
  "intent": "<INTENTION>",
  "confidence": <float entre 0 et 1>,
  "all_scores": {<toutes les intentions avec leur score float>}
}

Message client : """

GENERATION_PROMPT = """\
Tu es FreeAssist, l'assistant IA des conseillers de support technique de Free Mobile/Freebox.
Ton rôle est de rédiger une réponse professionnelle, empathique et précise pour aider
le conseiller à répondre au client.

Intention détectée : {intent}
Message du client : {text}

Rédige une réponse courte (3-5 phrases) directement utilisable par le conseiller."""


class OpenAIIntentClassifier:
    """GPT-4o-mini based intent classifier — same interface as IntentClassifier."""

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._loaded = True

    def load(self) -> None:
        logger.info("OpenAI intent classifier ready (fallback mode)")

    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, text: str) -> IntentPrediction:
        t0 = time.perf_counter()
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": INTENT_PROMPT + text},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )
        raw = response.choices[0].message.content or "{}"
        data: dict = json.loads(raw)

        intent = data.get("intent", "OTHER")
        confidence = float(data.get("confidence", 0.7))
        all_scores: dict[str, float] = data.get("all_scores", {i: 0.0 for i in INTENTS})

        # Ensure all intents present
        for i in INTENTS:
            if i not in all_scores:
                all_scores[i] = 0.0

        logger.debug("OpenAI intent", intent=intent, ms=int((time.perf_counter() - t0) * 1000))
        return IntentPrediction(
            intent=intent,
            confidence=round(confidence, 4),
            all_scores={k: round(v, 4) for k, v in all_scores.items()},
        )


class OpenAIRAGResult:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.source_documents: list[str] = ["gpt-4o-mini (mode fallback — modèles locaux non chargés)"]


class OpenAIRAGService:
    """gpt-4o-mini response generation — same interface as FreeAssistRAG."""

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._loaded = True

    def load(self) -> None:
        logger.info("OpenAI RAG service ready (fallback mode)")

    def is_loaded(self) -> bool:
        return self._loaded

    def generate(self, text: str, intent: str = "OTHER") -> OpenAIRAGResult:
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es FreeAssist, assistant IA pour les conseillers support Free.",
                },
                {
                    "role": "user",
                    "content": GENERATION_PROMPT.format(intent=intent, text=text),
                },
            ],
            temperature=0.3,
            max_tokens=400,
        )
        answer = response.choices[0].message.content or ""
        return OpenAIRAGResult(answer=answer)
