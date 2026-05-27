#!/usr/bin/env bash
# =============================================================================
# FreeAssist — Pipeline d'entraînement complet (Vast.ai H100)
#
# Exécute dans l'ordre :
#   1. Installation des dépendances
#   2. Génération de données augmentées via GPT-4o-mini
#   3. Génération des splits train/val/test
#   4. Fine-tuning CamemBERT
#   5. Évaluation sur test set
#   6. Copie des artefacts vers /workspace/artifacts/
#
# Usage (sur l'instance Vast.ai) :
#   export OPENAI_API_KEY=sk-...
#   export MLFLOW_TRACKING_URI=http://YOUR_MLFLOW_HOST:5000  # optionnel
#   bash scripts/run_training.sh
#
# Durée estimée sur H100 : ~25 minutes total
# =============================================================================

set -euo pipefail  # arrêt immédiat sur toute erreur

WORKSPACE=/workspace
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ARTIFACTS_DIR="$WORKSPACE/artifacts"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log() { echo "[$(date '+%H:%M:%S')] $*"; }
err() { echo "[ERROR] $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 0. Validation des prérequis
# ---------------------------------------------------------------------------
log "=== FreeAssist Training Pipeline ==="
log "Project dir : $PROJECT_DIR"
log "Timestamp   : $TIMESTAMP"

[[ -z "${OPENAI_API_KEY:-}" ]] && err "OPENAI_API_KEY not set. Run: export OPENAI_API_KEY=sk-..."

cd "$PROJECT_DIR"

# ---------------------------------------------------------------------------
# 1. Installation des dépendances
# ---------------------------------------------------------------------------
log "--- Step 1/5: Installing dependencies ---"
pip install --quiet --upgrade pip
# Upgrade torch first so transformers can resolve freely, then install remaining deps
pip install --quiet --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install --quiet \
    transformers datasets accelerate \
    scikit-learn numpy pandas \
    mlflow sentencepiece \
    openai \
    bitsandbytes peft

log "Dependencies installed ✓"

# ---------------------------------------------------------------------------
# 2. Augmentation via GPT-4o-mini
# ---------------------------------------------------------------------------
TEMPLATES_FILE="data/simulator/augmented_templates.json"
log "--- Step 2/5: Generating augmented templates via GPT-4o-mini ---"

if [[ -f "$TEMPLATES_FILE" ]]; then
    log "Templates already exist at $TEMPLATES_FILE — skipping generation"
else
    python data/simulator/augment_gpt.py \
        --api-key "$OPENAI_API_KEY" \
        --variants "${AUGMENT_VARIANTS:-100}" \
        --output "$TEMPLATES_FILE"
    log "Augmented templates generated ✓"
fi

# Vérification
TEMPLATE_COUNT=$(python -c "import json; d=json.load(open('$TEMPLATES_FILE')); print(sum(len(v) for v in d['intents'].values()))")
log "Total augmented conversations: $TEMPLATE_COUNT"

# ---------------------------------------------------------------------------
# 3. Génération des splits train / val / test
# ---------------------------------------------------------------------------
log "--- Step 3/5: Generating train/val/test splits ---"
python data/simulator/generate.py \
    --all \
    --templates-file "$TEMPLATES_FILE"

# Vérification des fichiers générés
for split in train val test; do
    JSONL="data/processed/$split/intent_classification.jsonl"
    [[ -f "$JSONL" ]] || err "Missing: $JSONL"
    COUNT=$(wc -l < "$JSONL")
    log "  $split: $COUNT samples ✓"
done

# ---------------------------------------------------------------------------
# 4. Fine-tuning CamemBERT
# ---------------------------------------------------------------------------
log "--- Step 4/5: Fine-tuning CamemBERT-base ---"
MLFLOW_URI="${MLFLOW_TRACKING_URI:-file://$WORKSPACE/mlruns}"
log "MLflow URI: $MLFLOW_URI"

python ml/training/train_intent_classifier.py \
    --train-file data/processed/train/intent_classification.jsonl \
    --val-file   data/processed/val/intent_classification.jsonl \
    --test-file  data/processed/test/intent_classification.jsonl \
    --output-dir ml/models/intent_classifier \
    --epochs     8 \
    --batch-size 32 \
    --lr         2e-5 \
    --mlflow-uri "$MLFLOW_URI" \
    --experiment "freeassist-intent-classifier-$TIMESTAMP"

log "Fine-tuning complete ✓"

# ---------------------------------------------------------------------------
# 5. Évaluation standalone sur test set
# ---------------------------------------------------------------------------
log "--- Step 5/5: Standalone evaluation ---"
python ml/evaluation/evaluate_classifier.py \
    --model-dir  ml/models/intent_classifier/best \
    --test-file  data/processed/test/intent_classification.jsonl \
    --output     ml/evaluation/results \
    --run-name   "camembert-$TIMESTAMP" \
    --mlflow-uri "$MLFLOW_URI"

# ---------------------------------------------------------------------------
# 6. Sauvegarde des artefacts
# ---------------------------------------------------------------------------
log "--- Saving artifacts ---"
mkdir -p "$ARTIFACTS_DIR"

# Modèle
cp -r ml/models/intent_classifier/best "$ARTIFACTS_DIR/intent_classifier_$TIMESTAMP"

# Données de test (pour pouvoir re-évaluer)
cp data/processed/test/intent_classification.jsonl "$ARTIFACTS_DIR/"

# Templates augmentés (pour ne pas re-payer GPT)
cp "$TEMPLATES_FILE" "$ARTIFACTS_DIR/"

# Rapports d'évaluation
cp ml/evaluation/results/*.json "$ARTIFACTS_DIR/" 2>/dev/null || true
cp ml/evaluation/results/*.csv  "$ARTIFACTS_DIR/" 2>/dev/null || true

# MLflow runs locaux
if [[ -d "$WORKSPACE/mlruns" ]]; then
    cp -r "$WORKSPACE/mlruns" "$ARTIFACTS_DIR/" 2>/dev/null || true
fi

log ""
log "================================================================"
log "  TRAINING PIPELINE COMPLETE"
log "================================================================"
log "  Artifacts saved to : $ARTIFACTS_DIR"
log "  Model checkpoint   : $ARTIFACTS_DIR/intent_classifier_$TIMESTAMP"
log ""
log "  Next steps:"
log "  1. vastai copy INSTANCE_ID:$ARTIFACTS_DIR/ ./artifacts/"
log "  2. vastai destroy instance INSTANCE_ID"
log "  3. Upload model to Fly.io volume"
log "================================================================"
