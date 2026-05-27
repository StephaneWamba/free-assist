"""
FreeAssist — Inference Server (runs on Vast.ai)

Serves CamemBERT intent classification + RAG generation.
Called by Fly.io API as primary ML backend.

Endpoints:
  POST /predict  → intent classification
  POST /generate → RAG response
  GET  /health   → liveness check
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_DIR = os.environ.get("MODEL_DIR", "/workspace/artifacts/best")
KB_DIR = os.environ.get("KB_DIR", "/workspace/data/knowledge_base")

app = FastAPI(title="FreeAssist Inference", version="0.1.0")

# Lazy-loaded singletons
_classifier = None
_rag = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from transformers import pipeline
        import torch
        _classifier = pipeline(
            task="text-classification",
            model=MODEL_DIR,
            tokenizer=MODEL_DIR,
            device=0 if torch.cuda.is_available() else -1,
            top_k=None,
            truncation=True,
            max_length=128,
        )
    return _classifier


def _get_rag():
    global _rag
    if _rag is None:
        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="dangvantuan/sentence-camembert-large")
        index_path = Path(MODEL_DIR).parent / "faiss_index"
        if index_path.exists():
            _rag = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
    return _rag


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    text: str

class PredictResponse(BaseModel):
    intent: str
    confidence: float
    all_scores: dict[str, float]
    latency_ms: int

class GenerateRequest(BaseModel):
    text: str
    intent: str

class GenerateResponse(BaseModel):
    answer: str
    sources: list[str]
    latency_ms: int


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    model_ok = Path(MODEL_DIR).exists()
    return {
        "status": "ok" if model_ok else "no_model",
        "model_dir": MODEL_DIR,
        "cuda": _cuda_available(),
    }

def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    t0 = time.perf_counter()
    try:
        clf = _get_classifier()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Model not ready: {e}")

    results = clf(req.text)[0]  # list of {label, score}
    all_scores = {r["label"]: round(r["score"], 4) for r in results}
    top = max(results, key=lambda r: r["score"])

    return PredictResponse(
        intent=top["label"],
        confidence=round(top["score"], 4),
        all_scores=all_scores,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    t0 = time.perf_counter()
    rag = _get_rag()

    if rag:
        docs = rag.similarity_search(req.text, k=3)
        context = "\n\n".join(d.page_content for d in docs)
        sources = [d.metadata.get("source", "KB") for d in docs]
    else:
        context = ""
        sources = ["no_index"]

    # Simple template-based response with context
    if context:
        answer = (
            f"Basé sur notre base de connaissance pour l'intention {req.intent} :\n\n"
            f"{context[:800]}"
        )
    else:
        answer = f"Intention détectée : {req.intent}. Aucun document RAG disponible."

    return GenerateResponse(
        answer=answer,
        sources=sources,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
