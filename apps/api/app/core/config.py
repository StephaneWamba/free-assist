"""
FreeAssist — Application Settings

Loaded from environment variables (Fly.io secrets in prod, .env in dev).
PostgreSQL + Redis are optional for the lite/demo mode.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "FreeAssist API"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Database (optional — SQLite used if absent)
    database_url: str = "sqlite:////app/data/freeassist.db"

    # Redis (optional — disabled if absent)
    redis_url: Optional[str] = None

    # ML Models
    intent_classifier_path: str = "/app/models/intent_classifier/best"
    rag_index_dir: str = "/app/models/faiss_index"
    llm_model_id: str = "mistralai/Mistral-7B-Instruct-v0.3"
    embed_model_id: str = "dangvantuan/sentence-camembert-large"
    device: Literal["cpu", "cuda", "mps"] = "cpu"

    # Remote inference server (Vast.ai) — primary ML backend
    inference_url: Optional[str] = None  # e.g. http://ssh2.vast.ai:PORT

    # OpenAI (fallback when inference server is not available)
    openai_api_key: Optional[str] = None

    # HuggingFace
    hf_token: Optional[str] = None

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "freeassist-production"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://freeassist-web.vercel.app",
    ]

    # Security
    secret_key: str = Field(default="change_me_in_production_use_openssl_rand_hex_32")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
