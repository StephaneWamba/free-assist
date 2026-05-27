# Build context: repo root (docker build -f apps/api/Dockerfile .)
# Fly.io lite image — OpenAI fallback only, no ML deps (~200MB vs 2.9GB)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml .
RUN pip install --upgrade pip && pip install -e ".[lite]"

COPY apps/api/app/ ./app/
COPY ml/utils/ ./ml/utils/
COPY data/knowledge_base/ ./data/knowledge_base/

RUN mkdir -p /app/data /app/models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
