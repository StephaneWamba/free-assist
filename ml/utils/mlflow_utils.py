"""
FreeAssist — MLflow Utilities

Thin helpers around mlflow to keep experiment tracking DRY across training scripts.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

import mlflow


TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def setup(experiment_name: str) -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(experiment_name)


@contextmanager
def run(run_name: str, tags: dict[str, str] | None = None) -> Generator[mlflow.ActiveRun, None, None]:
    with mlflow.start_run(run_name=run_name, tags=tags or {}) as active_run:
        yield active_run


def log_dataset_info(name: str, n_samples: int, split: str) -> None:
    mlflow.log_params({f"dataset_{split}_name": name, f"dataset_{split}_size": n_samples})


def log_classification_report(report: dict[str, Any], prefix: str = "") -> None:
    """Log per-class F1 scores from sklearn classification_report dict."""
    for label, metrics in report.items():
        if isinstance(metrics, dict):
            for metric_name, value in metrics.items():
                mlflow.log_metric(f"{prefix}{label}_{metric_name}", value)
