#!/usr/bin/env bash
# FreeAssist — Lance le serveur d'inférence sur Vast.ai (port 8080)
# Usage: bash scripts/serve_inference.sh

set -euo pipefail

WORKSPACE=/workspace
MODEL_DIR="$WORKSPACE/artifacts/best"
PORT=8080

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "=== FreeAssist Inference Server ==="
log "Model dir : $MODEL_DIR"
log "Port      : $PORT"

[[ -d "$MODEL_DIR" ]] || { echo "[ERROR] Model not found at $MODEL_DIR — run training first"; exit 1; }

cd "$WORKSPACE"

# Install inference deps (minimal)
pip install --quiet fastapi uvicorn langchain-community langchain-huggingface faiss-cpu

log "Starting inference server on port $PORT..."
export MODEL_DIR="$MODEL_DIR"
export KB_DIR="$WORKSPACE/data/knowledge_base"

nohup uvicorn apps.inference.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    > "$WORKSPACE/inference.log" 2>&1 &

echo "PID: $!"
log "Server started. Logs: $WORKSPACE/inference.log"
log "Health: http://localhost:$PORT/health"
