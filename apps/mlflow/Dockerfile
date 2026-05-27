FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --upgrade pip && pip install "mlflow==2.14.3"

RUN mkdir -p /mlflow/tracking/artifacts && chmod -R 777 /mlflow

EXPOSE 5000

CMD ["mlflow", "server", \
     "--host", "0.0.0.0", \
     "--port", "5000", \
     "--workers", "2", \
     "--backend-store-uri", "sqlite:////mlflow/tracking/mlflow.db", \
     "--artifacts-destination", "/mlflow/tracking/artifacts"]
