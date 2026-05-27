from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.api.v1.routes import assistant, experiments, health, stats, monitoring, models, knowledge_base, evaluation
from app.services.assistant_service import AssistantService
from app.services.stats_service import StatsService

logger = get_logger(__name__)
settings = get_settings()


def _ml_models_present() -> bool:
    classifier_path = Path(settings.intent_classifier_path)
    index_path = Path(settings.rag_index_dir)
    return classifier_path.exists() and index_path.exists()


def _load_ml_services():
    from app.services.intent_service import IntentClassifier
    from ml.rag.pipeline import FreeAssistRAG

    classifier = IntentClassifier(
        model_path=settings.intent_classifier_path,
        device=settings.device,
    )
    classifier.load()

    rag = FreeAssistRAG(
        index_dir=settings.rag_index_dir,
        llm_model_id=settings.llm_model_id,
    )
    rag.load()
    return classifier, rag


def _load_openai_services():
    from app.services.openai_fallback import OpenAIIntentClassifier, OpenAIRAGService

    api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY required when ML models are not present")

    classifier = OpenAIIntentClassifier(api_key=api_key)
    classifier.load()

    rag = OpenAIRAGService(api_key=api_key)
    rag.load()
    return classifier, rag


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(level=settings.log_level, json_logs=settings.environment == "production")
    logger.info("Starting FreeAssist API", environment=settings.environment)

    stats_svc = StatsService()
    app.state.stats_service = stats_svc
    app.state.ml_mode = "none"

    # Priority: remote inference > local models > OpenAI fallback
    summarizer = None
    try:
        if settings.inference_url:
            logger.info("Inference URL configured — trying Vast.ai server", url=settings.inference_url)
            from app.services.inference_client import RemoteClassifier
            from app.services.openai_fallback import OpenAIRAGService
            classifier = RemoteClassifier(settings.inference_url)
            classifier.load()
            if classifier.is_loaded():
                api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
                rag = OpenAIRAGService(api_key=api_key)
                rag.load()
                app.state.ml_mode = "remote"
                logger.info("Remote inference server ready (hybrid: CamemBERT + OpenAI RAG)")
            else:
                raise RuntimeError("Remote inference server unreachable")
        elif _ml_models_present():
            logger.info("ML models found — loading CamemBERT + Mistral RAG")
            classifier, rag = _load_ml_services()
            app.state.ml_mode = "local"
            try:
                from transformers import pipeline as hf_pipeline
                summarizer = hf_pipeline(
                    "summarization",
                    model="moussaKam/barthez-orangesum-abstract",
                    device=0 if settings.device == "cuda" else -1,
                    max_length=80,
                    min_length=20,
                )
            except Exception as e:
                logger.warning("Summarizer not loaded (non-critical)", error=str(e))
        else:
            logger.info("No inference server or local models — using OpenAI fallback")
            classifier, rag = _load_openai_services()
            app.state.ml_mode = "openai"

        app.state.assistant_service = AssistantService(
            classifier=classifier,
            rag=rag,
            stats=stats_svc,
            summarizer=summarizer,
        )
        logger.info("AssistantService ready", mode=app.state.ml_mode)

    except Exception as exc:
        logger.error("Failed to initialise AssistantService", error=str(exc))
        app.state.assistant_service = None  # health endpoint will report degraded

    yield

    logger.info("Shutting down FreeAssist API")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FreeAssist API",
        description="Agentic AI assistant for Iliad-Free technical support agents",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router,          prefix="/api/v1")
    app.include_router(assistant.router,       prefix="/api/v1")
    app.include_router(experiments.router,     prefix="/api/v1")
    app.include_router(stats.router,           prefix="/api/v1")
    app.include_router(monitoring.router,      prefix="/api/v1")
    app.include_router(models.router,          prefix="/api/v1")
    app.include_router(knowledge_base.router,  prefix="/api/v1")
    app.include_router(evaluation.router,      prefix="/api/v1")

    return app


app = create_app()
