"""
FreeAssist — Standalone Classifier Evaluation

Loads a saved CamemBERT checkpoint and evaluates it on any JSONL test set.
Run this after training to get a clean benchmark report, or to compare
multiple checkpoints.

Usage:
    python ml/evaluation/evaluate_classifier.py \\
        --model-dir ml/models/intent_classifier/best \\
        --test-file data/processed/test/intent_classification.jsonl \\
        --output    ml/evaluation/results/

    # Compare two checkpoints
    python ml/evaluation/evaluate_classifier.py \\
        --model-dir ml/models/intent_classifier/best \\
        --test-file data/processed/test/intent_classification.jsonl \\
        --mlflow-uri http://localhost:5000 --run-name eval-checkpoint-best
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    accuracy_score,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from torch.utils.data import DataLoader, Dataset

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTENTS = [
    "BOX_CONNECTIVITY", "BOX_REBOOT", "MOBILE_PORTABILITY", "BILLING_DISPUTE",
    "CONTRACT_CHANGE", "TECHNICAL_OUTAGE", "EQUIPMENT_RETURN",
    "SPEED_ISSUE", "CANCELLATION", "OTHER",
]
INTENT2ID = {intent: i for i, intent in enumerate(INTENTS)}
ID2INTENT  = {i: intent for i, intent in enumerate(INTENTS)}

MAX_LENGTH = 128


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class IntentDataset(Dataset):
    def __init__(self, records: list[dict], tokenizer):
        self.records   = records
        self.tokenizer = tokenizer

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict:
        record   = self.records[idx]
        encoding = self.tokenizer(
            record["text"],
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids":      encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "label_id":       record["label_id"],
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
# Inference
# ---------------------------------------------------------------------------


def run_inference(
    model: AutoModelForSequenceClassification,
    tokenizer: AutoTokenizer,
    records: list[dict],
    batch_size: int = 64,
    device: str = "cuda",
) -> tuple[list[int], list[int], list[float]]:
    """Returns (true_labels, pred_labels, latencies_ms)."""
    dataset    = IntentDataset(records, tokenizer)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=4)
    model.eval()

    all_preds:   list[int]   = []
    all_labels:  list[int]   = []
    all_latency: list[float] = []

    with torch.no_grad():
        for batch in dataloader:
            t0 = time.perf_counter()
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            outputs        = model(input_ids=input_ids, attention_mask=attention_mask)
            elapsed        = (time.perf_counter() - t0) * 1000 / len(batch["label_id"])

            preds = outputs.logits.argmax(dim=-1).cpu().numpy().tolist()
            all_preds.extend(preds)
            all_labels.extend(batch["label_id"].tolist())
            all_latency.extend([elapsed] * len(preds))

    return all_labels, all_preds, all_latency


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report(
    true_labels: list[int],
    pred_labels: list[int],
    latencies:   list[float],
    output_dir:  Path,
    run_name:    str,
) -> dict:
    f1_macro    = f1_score(true_labels, pred_labels, average="macro",    zero_division=0)
    f1_weighted = f1_score(true_labels, pred_labels, average="weighted", zero_division=0)
    accuracy    = accuracy_score(true_labels, pred_labels)
    avg_latency = float(np.mean(latencies))
    p99_latency = float(np.percentile(latencies, 99))

    report_str  = classification_report(
        true_labels, pred_labels,
        target_names=INTENTS,
        zero_division=0,
    )
    report_dict = classification_report(
        true_labels, pred_labels,
        target_names=INTENTS,
        output_dict=True,
        zero_division=0,
    )

    print(f"\n{'='*60}")
    print(f"  {run_name}")
    print(f"{'='*60}")
    print(report_str)
    print(f"  F1 macro    : {f1_macro:.4f}")
    print(f"  F1 weighted : {f1_weighted:.4f}")
    print(f"  Accuracy    : {accuracy:.4f}")
    print(f"  Latency avg : {avg_latency:.1f}ms / p99: {p99_latency:.1f}ms")
    print(f"{'='*60}\n")

    # Confusion matrix CSV
    cm = confusion_matrix(true_labels, pred_labels, labels=list(range(len(INTENTS))))
    cm_lines = ["," + ",".join(INTENTS)]
    for i, row in enumerate(cm):
        cm_lines.append(INTENTS[i] + "," + ",".join(str(v) for v in row))

    output_dir.mkdir(parents=True, exist_ok=True)
    cm_path = output_dir / f"confusion_matrix_{run_name}.csv"
    cm_path.write_text("\n".join(cm_lines), encoding="utf-8")

    # Full report JSON
    summary = {
        "run_name":    run_name,
        "f1_macro":    round(f1_macro,    4),
        "f1_weighted": round(f1_weighted, 4),
        "accuracy":    round(accuracy,    4),
        "avg_latency_ms": round(avg_latency, 2),
        "p99_latency_ms": round(p99_latency, 2),
        "n_samples":   len(true_labels),
        "per_class": {
            intent: {
                "precision": round(report_dict[intent]["precision"], 4),
                "recall":    round(report_dict[intent]["recall"],    4),
                "f1":        round(report_dict[intent]["f1-score"],  4),
                "support":   report_dict[intent]["support"],
            }
            for intent in INTENTS if intent in report_dict
        },
    }

    report_path = output_dir / f"report_{run_name}.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Report saved to {report_path}")
    print(f"✓ Confusion matrix saved to {cm_path}")

    return summary


# ---------------------------------------------------------------------------
# MLflow logging (optional)
# ---------------------------------------------------------------------------


def log_to_mlflow(summary: dict, model_dir: str, mlflow_uri: str, run_name: str) -> None:
    try:
        import mlflow
        mlflow.set_tracking_uri(mlflow_uri)
        mlflow.set_experiment("freeassist-evaluation")
        with mlflow.start_run(run_name=run_name):
            mlflow.log_param("model_dir",   model_dir)
            mlflow.log_param("n_samples",   summary["n_samples"])
            mlflow.log_metrics({
                "test/f1_macro":       summary["f1_macro"],
                "test/f1_weighted":    summary["f1_weighted"],
                "test/accuracy":       summary["accuracy"],
                "test/avg_latency_ms": summary["avg_latency_ms"],
                "test/p99_latency_ms": summary["p99_latency_ms"],
            })
            for intent, metrics in summary["per_class"].items():
                mlflow.log_metrics({
                    f"test/{intent}/f1":        metrics["f1"],
                    f"test/{intent}/precision": metrics["precision"],
                    f"test/{intent}/recall":    metrics["recall"],
                })
        print("✓ Metrics logged to MLflow")
    except Exception as exc:
        print(f"[!] MLflow logging failed (non-critical): {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate FreeAssist intent classifier")
    parser.add_argument("--model-dir",  required=True,  help="Path to saved model directory")
    parser.add_argument("--test-file",  required=True,  help="Path to test JSONL file")
    parser.add_argument("--output",     default="ml/evaluation/results", help="Output directory for reports")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--run-name",   default="eval", help="Name for this evaluation run")
    parser.add_argument("--mlflow-uri", default=os.environ.get("MLFLOW_TRACKING_URI", ""), help="MLflow tracking URI (optional)")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    print(f"Loading model from {args.model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model     = AutoModelForSequenceClassification.from_pretrained(args.model_dir).to(device)

    print(f"Loading test data from {args.test_file}")
    records = load_jsonl(args.test_file)
    print(f"Test samples: {len(records)}")

    true_labels, pred_labels, latencies = run_inference(
        model, tokenizer, records,
        batch_size=args.batch_size,
        device=device,
    )

    summary = build_report(
        true_labels, pred_labels, latencies,
        output_dir=Path(args.output),
        run_name=args.run_name,
    )

    if args.mlflow_uri:
        log_to_mlflow(summary, args.model_dir, args.mlflow_uri, args.run_name)

    # Exit code based on quality gate
    if summary["f1_macro"] < 0.75:
        print(f"\n⚠ F1 macro {summary['f1_macro']:.3f} < 0.75 — model needs improvement")
        raise SystemExit(1)
    elif summary["f1_macro"] >= 0.90:
        print(f"\n✓ Excellent — F1 macro {summary['f1_macro']:.3f} ≥ 0.90")
    else:
        print(f"\n✓ Acceptable — F1 macro {summary['f1_macro']:.3f}")


if __name__ == "__main__":
    main()
