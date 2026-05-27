"""FreeAssist — Models status route."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter(prefix="/models", tags=["models"])
settings = get_settings()

MODEL_CATALOG = [
    {
        "id": "intent_classifier",
        "name": "CamemBERT Intent Classifier",
        "type": "classifier",
        "base_model": "camembert-base",
        "hf_id": "camembert/camembert-base",
        "task": "Classification d'intention (10 classes)",
        "language": "fr",
        "params_m": 111,
        "description": "Fine-tuné sur tickets support Free pour détecter l'intention client.",
    },
    {
        "id": "llm",
        "name": "Mistral-7B Instruct",
        "type": "llm",
        "base_model": "Mistral-7B-Instruct-v0.3",
        "hf_id": "mistralai/Mistral-7B-Instruct-v0.3",
        "task": "Génération de réponse (RAG)",
        "language": "fr/en",
        "params_m": 7241,
        "description": "Génère la réponse conseiller via LangGraph RAG sur la base de connaissances Free.",
    },
    {
        "id": "embeddings",
        "name": "Sentence-CamemBERT-Large",
        "type": "embeddings",
        "base_model": "sentence-camembert-large",
        "hf_id": "dangvantuan/sentence-camembert-large",
        "task": "Embeddings sémantiques (FAISS index)",
        "language": "fr",
        "params_m": 337,
        "description": "Encode les documents de la base de connaissances pour la recherche vectorielle.",
    },
    {
        "id": "fallback_intent",
        "name": "GPT-4o-mini (fallback)",
        "type": "classifier",
        "base_model": "gpt-4o-mini",
        "hf_id": None,
        "task": "Classification d'intention via OpenAI API",
        "language": "fr/en",
        "params_m": None,
        "description": "Utilisé en mode fallback quand les modèles locaux ne sont pas encore chargés.",
    },
    {
        "id": "fallback_llm",
        "name": "GPT-4o-mini (fallback)",
        "type": "llm",
        "base_model": "gpt-4o-mini",
        "hf_id": None,
        "task": "Génération de réponse via OpenAI API",
        "language": "fr/en",
        "params_m": None,
        "description": "Utilisé en mode fallback pour la génération de réponse conseiller.",
    },
]


@router.get("")
async def list_models(request: Request) -> dict:
    service = getattr(request.app.state, "assistant_service", None)
    ml_mode = getattr(request.app.state, "ml_mode", "none")

    classifier_loaded = bool(service and service._classifier.is_loaded())
    rag_loaded = bool(service and service._rag.is_loaded())
    device = settings.device

    models = []
    for m in MODEL_CATALOG:
        is_local = m["hf_id"] is not None
        is_fallback = m["id"].startswith("fallback_")

        if ml_mode == "local":
            if m["id"] == "intent_classifier":
                status = "active" if classifier_loaded else "loading"
            elif m["id"] == "llm":
                status = "active" if rag_loaded else "loading"
            elif m["id"] == "embeddings":
                status = "active" if rag_loaded else "loading"
            else:
                status = "standby"
        elif ml_mode == "remote":
            # Hybrid: CamemBERT classifies remotely, OpenAI generates
            if m["id"] == "intent_classifier":
                status = "active" if classifier_loaded else "loading"
            elif m["id"] == "fallback_llm":
                status = "active" if rag_loaded else "loading"
            elif m["id"] in ("llm", "embeddings"):
                status = "standby"  # local LLM/embeddings not used in remote mode
            else:
                status = "standby"
        elif ml_mode == "openai":
            if is_fallback:
                status = "active"
            else:
                status = "not_loaded"
        else:
            status = "not_loaded"

        models.append({
            **m,
            "status": status,
            "device": device if (status == "active" and is_local) else None,
        })

    return {
        "ml_mode": ml_mode,
        "device": device,
        "models": models,
    }
