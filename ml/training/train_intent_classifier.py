"""
FreeAssist — CamemBERT Intent Classifier — Fine-tuning

Pipeline complet :
  1. Charge les données train/val/test (JSONL)
  2. Fine-tune camembert-base sur 10 classes d'intention
  3. Évalue sur val à chaque epoch (early stopping)
  4. Évalue sur test set final (jamais vu pendant l'entraînement)
  5. Log toutes les métriques + matrice de confusion dans MLflow
  6. Sauvegarde le meilleur modèle

Usage (sur Vast.ai H100) :
    python ml/training/train_intent_classifier.py \\
        --train-file data/processed/train/intent_classification.jsonl \\
        --val-file   data/processed/val/intent_classification.jsonl \\
        --test-file  data/processed/test/intent_classification.jsonl \\
        --output-dir ml/models/intent_classifier \\
        --epochs 8 --batch-size 32 --lr 2e-5
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import mlflow
import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)
from torch.utils.data import Dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTENTS = [
    "BOX_CONNECTIVITY",
    "BOX_REBOOT",
    "MOBILE_PORTABILITY",
    "BILLING_DISPUTE",
    "CONTRACT_CHANGE",
    "TECHNICAL_OUTAGE",
    "EQUIPMENT_RETURN",
    "SPEED_ISSUE",
    "CANCELLATION",
    "OTHER",
]
INTENT2ID = {intent: i for i, intent in enumerate(INTENTS)}
ID2INTENT = {i: intent for i, intent in enumerate(INTENTS)}

BASE_MODEL = "camembert-base"
MAX_LENGTH = 128


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class IntentDataset(Dataset):
    def __init__(self, records: list[dict], tokenizer, max_length: int = MAX_LENGTH):
        self.records = records
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict:
        record = self.records[idx]
        encoding = self.tokenizer(
            record["text"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(record["label_id"], dtype=torch.long),
        }


def load_jsonl(path: str | Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_metrics(eval_pred) -> dict[str, float]:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    f1_macro    = f1_score(labels, preds, average="macro",    zero_division=0)
    f1_weighted = f1_score(labels, preds, average="weighted", zero_division=0)
    accuracy    = float((preds == labels).mean())
    return {
        "accuracy":    accuracy,
        "f1_macro":    f1_macro,
        "f1_weighted": f1_weighted,
    }


def detailed_evaluation(
    trainer: Trainer,
    dataset: IntentDataset,
    records: list[dict],
    split_name: str,
) -> dict[str, float]:
    """Run prediction, compute per-class metrics + confusion matrix, log to MLflow."""
    output = trainer.predict(dataset)
    preds  = np.argmax(output.predictions, axis=-1)
    labels = [r["label_id"] for r in records]

    # Per-class metrics
    report_dict = classification_report(
        labels, preds,
        target_names=INTENTS,
        output_dict=True,
        zero_division=0,
    )
    report_str = classification_report(
        labels, preds,
        target_names=INTENTS,
        zero_division=0,
    )
    logger.info(f"\n=== {split_name.upper()} SET ===\n{report_str}")

    # Confusion matrix → save as CSV artifact
    cm = confusion_matrix(labels, preds, labels=list(range(len(INTENTS))))
    cm_lines = ["," + ",".join(INTENTS)]
    for i, row in enumerate(cm):
        cm_lines.append(INTENTS[i] + "," + ",".join(str(v) for v in row))
    cm_path = Path(f"/tmp/confusion_matrix_{split_name}.csv")
    cm_path.write_text("\n".join(cm_lines))
    mlflow.log_artifact(str(cm_path), artifact_path="confusion_matrices")

    # Log per-class F1 to MLflow
    per_class_metrics: dict[str, float] = {}
    for intent in INTENTS:
        if intent in report_dict:
            per_class_metrics[f"{split_name}/{intent}/f1"]       = report_dict[intent]["f1-score"]
            per_class_metrics[f"{split_name}/{intent}/precision"] = report_dict[intent]["precision"]
            per_class_metrics[f"{split_name}/{intent}/recall"]    = report_dict[intent]["recall"]
    mlflow.log_metrics(per_class_metrics)

    # Global metrics
    global_metrics = {
        f"{split_name}/accuracy":    report_dict["accuracy"],
        f"{split_name}/f1_macro":    report_dict["macro avg"]["f1-score"],
        f"{split_name}/f1_weighted": report_dict["weighted avg"]["f1-score"],
    }
    mlflow.log_metrics(global_metrics)

    return global_metrics


# ---------------------------------------------------------------------------
# Training config
# ---------------------------------------------------------------------------


@dataclass
class TrainingConfig:
    train_file: str
    val_file: str
    test_file: str
    output_dir: str
    epochs: int = 8
    batch_size: int = 32
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    seed: int = 42
    fp16: bool = True
    gradient_accumulation_steps: int = 1
    early_stopping_patience: int = 3
    mlflow_experiment: str = "freeassist-intent-classifier"
    mlflow_tracking_uri: str = "http://localhost:5000"


# ---------------------------------------------------------------------------
# Main training function
# ---------------------------------------------------------------------------


def train(config: TrainingConfig) -> None:
    set_seed(config.seed)
    mlflow.set_tracking_uri(config.mlflow_tracking_uri)
    mlflow.set_experiment(config.mlflow_experiment)

    logger.info(f"Loading base model: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(INTENTS),
        id2label=ID2INTENT,
        label2id=INTENT2ID,
    )

    logger.info("Loading datasets")
    train_records = load_jsonl(config.train_file)
    val_records   = load_jsonl(config.val_file)
    test_records  = load_jsonl(config.test_file)
    logger.info(
        f"Train: {len(train_records)} | Val: {len(val_records)} | Test: {len(test_records)}"
    )

    train_dataset = IntentDataset(train_records, tokenizer)
    val_dataset   = IntentDataset(val_records,   tokenizer)
    test_dataset  = IntentDataset(test_records,  tokenizer)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size * 2,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        warmup_ratio=config.warmup_ratio,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        fp16=config.fp16 and torch.cuda.is_available(),
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_steps=25,
        report_to=[],          # MLflow tracked manually for full control
        seed=config.seed,
        dataloader_num_workers=4,
        save_total_limit=2,    # keep only best + last checkpoint
    )

    with mlflow.start_run(run_name=f"camembert-ep{config.epochs}-bs{config.batch_size}"):
        mlflow.log_params({
            "base_model":   BASE_MODEL,
            "epochs":       config.epochs,
            "batch_size":   config.batch_size,
            "lr":           config.learning_rate,
            "weight_decay": config.weight_decay,
            "warmup_ratio": config.warmup_ratio,
            "fp16":         config.fp16,
            "train_samples": len(train_records),
            "val_samples":   len(val_records),
            "test_samples":  len(test_records),
            "num_classes":  len(INTENTS),
            "max_length":   MAX_LENGTH,
            "seed":         config.seed,
        })

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=config.early_stopping_patience)],
        )

        logger.info("Starting training")
        train_result = trainer.train()
        mlflow.log_metrics({
            "train/runtime_s":       train_result.metrics["train_runtime"],
            "train/samples_per_sec": train_result.metrics["train_samples_per_second"],
        })

        # ── Validation evaluation ──────────────────────────────────────────
        logger.info("Evaluating on validation set")
        detailed_evaluation(trainer, val_dataset, val_records, split_name="val")

        # ── Test evaluation (held-out — evaluated once only) ───────────────
        logger.info("Evaluating on TEST set (held-out)")
        test_metrics = detailed_evaluation(trainer, test_dataset, test_records, split_name="test")
        logger.info(f"TEST RESULTS: {test_metrics}")

        # ── Save model ────────────────────────────────────────────────────
        model_path = output_dir / "best"
        trainer.save_model(str(model_path))
        tokenizer.save_pretrained(str(model_path))

        label_map = {"id2label": ID2INTENT, "label2id": INTENT2ID, "intents": INTENTS}
        label_map_path = model_path / "label_map.json"
        label_map_path.write_text(json.dumps(label_map, indent=2))

        mlflow.log_artifact(str(model_path), artifact_path="model")
        logger.info(f"Model saved to {model_path}")

        # Summary
        f1 = test_metrics.get("test/f1_macro", 0)
        acc = test_metrics.get("test/accuracy", 0)
        logger.info(f"\n{'='*50}")
        logger.info(f"FINAL TEST F1 macro : {f1:.4f}")
        logger.info(f"FINAL TEST Accuracy  : {acc:.4f}")
        logger.info(f"{'='*50}")

        if f1 < 0.80:
            logger.warning("F1 macro < 0.80 — consider more data or longer training")
        elif f1 >= 0.90:
            logger.info("Excellent — F1 macro ≥ 0.90 ✓")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Train FreeAssist CamemBERT intent classifier")
    parser.add_argument("--train-file",  required=True)
    parser.add_argument("--val-file",    required=True)
    parser.add_argument("--test-file",   required=True)
    parser.add_argument("--output-dir",  default="ml/models/intent_classifier")
    parser.add_argument("--epochs",      type=int,   default=8)
    parser.add_argument("--batch-size",  type=int,   default=32)
    parser.add_argument("--lr",          type=float, default=2e-5)
    parser.add_argument("--seed",        type=int,   default=42)
    parser.add_argument("--no-fp16",     action="store_true")
    parser.add_argument("--mlflow-uri",  default=os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    parser.add_argument("--experiment",  default="freeassist-intent-classifier")
    args = parser.parse_args()

    config = TrainingConfig(
        train_file=args.train_file,
        val_file=args.val_file,
        test_file=args.test_file,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed,
        fp16=not args.no_fp16,
        mlflow_experiment=args.experiment,
        mlflow_tracking_uri=args.mlflow_uri,
    )
    train(config)


if __name__ == "__main__":
    main()
