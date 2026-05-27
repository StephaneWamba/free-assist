"""
FreeAssist — Evaluation Pipeline

Benchmarks three approaches side by side:
  1. Zero-shot prompting
  2. RAG + base LLM
  3. RAG + QLoRA fine-tuned

Uses:
  - evaluate (HuggingFace) for ROUGE, BERTScore
  - ragas for RAG-specific metrics (faithfulness, answer relevancy, context recall)
  - LLM-as-judge for qualitative scoring
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import evaluate as hf_evaluate
import mlflow
import pandas as pd
from ragas import evaluate as ragas_evaluate
from ragas.metrics import (
    answer_relevancy,
    context_recall,
    faithfulness,
)
from datasets import Dataset as HFDataset


# ---------------------------------------------------------------------------
# Metrics bundles
# ---------------------------------------------------------------------------

_rouge = hf_evaluate.load("rouge")
_bertscore = hf_evaluate.load("bertscore")


@dataclass
class NLGMetrics:
    rouge1: float
    rouge2: float
    rougeL: float
    bertscore_f1: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class RAGMetrics:
    faithfulness: float          # Is the answer grounded in the context?
    answer_relevancy: float      # Is the answer relevant to the question?
    context_recall: float        # Does the context cover the ground truth?

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class BenchmarkResult:
    model_name: str
    nlg: NLGMetrics
    rag: RAGMetrics | None
    avg_latency_ms: float
    n_samples: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "rouge1": self.nlg.rouge1,
            "rouge2": self.nlg.rouge2,
            "rougeL": self.nlg.rougeL,
            "bertscore_f1": self.nlg.bertscore_f1,
            **(self.rag.to_dict() if self.rag else {}),
            "avg_latency_ms": self.avg_latency_ms,
            "n_samples": self.n_samples,
        }


# ---------------------------------------------------------------------------
# NLG scoring
# ---------------------------------------------------------------------------


def compute_nlg_metrics(predictions: list[str], references: list[str]) -> NLGMetrics:
    rouge_result = _rouge.compute(predictions=predictions, references=references)
    bs_result = _bertscore.compute(
        predictions=predictions,
        references=references,
        lang="fr",
        model_type="camembert-base",
    )
    return NLGMetrics(
        rouge1=rouge_result["rouge1"],
        rouge2=rouge_result["rouge2"],
        rougeL=rouge_result["rougeL"],
        bertscore_f1=sum(bs_result["f1"]) / len(bs_result["f1"]),
    )


# ---------------------------------------------------------------------------
# RAG scoring via RAGAS
# ---------------------------------------------------------------------------


def compute_rag_metrics(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> RAGMetrics:
    """Use RAGAS to evaluate RAG-specific quality dimensions."""
    dataset = HFDataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    result = ragas_evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_recall],
    )
    scores = result.to_pandas()

    return RAGMetrics(
        faithfulness=scores["faithfulness"].mean(),
        answer_relevancy=scores["answer_relevancy"].mean(),
        context_recall=scores["context_recall"].mean(),
    )


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def run_benchmark(
    test_file: str | Path,
    results_dir: str | Path,
    experiment_name: str = "freeassist-benchmark",
) -> list[BenchmarkResult]:
    """
    Load test samples, run each model variant, compute all metrics, log to MLflow.
    Returns list of BenchmarkResult for downstream reporting.
    """
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(test_file, encoding="utf-8") as f:
        samples = [json.loads(l) for l in f if l.strip()]

    print(f"Evaluating on {len(samples)} test samples")

    # In a real run: load each model variant and generate predictions.
    # Here we expose the scaffold — plug in your pipeline.generate() calls.
    all_results: list[BenchmarkResult] = []

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="full-benchmark"):
        for result in all_results:
            mlflow.log_metrics(
                {f"{result.model_name}/{k}": v for k, v in result.to_dict().items() if isinstance(v, float)},
            )

        # Persist benchmark table
        df = pd.DataFrame([r.to_dict() for r in all_results])
        out_path = results_dir / "benchmark.csv"
        df.to_csv(out_path, index=False)
        mlflow.log_artifact(str(out_path))
        print(f"\nBenchmark results:\n{df.to_string()}")

    return all_results


# ---------------------------------------------------------------------------
# LLM-as-judge
# ---------------------------------------------------------------------------


def llm_judge_score(
    question: str,
    answer: str,
    reference: str,
    judge_client: Any,  # openai.OpenAI or anthropic.Anthropic compatible
) -> dict[str, float | str]:
    """
    Ask an LLM to score the answer on 3 dimensions (1-5 scale).
    Decoupled from any specific provider — pass any client.
    """
    prompt = f"""Tu es un expert du support client télécom. Évalue cette réponse d'agent sur 3 critères (note de 1 à 5).

Question / Ticket client :
{question}

Réponse de l'agent :
{answer}

Réponse de référence :
{reference}

Réponds UNIQUEMENT en JSON avec ce format :
{{"accuracy": <1-5>, "clarity": <1-5>, "completeness": <1-5>, "reasoning": "<explication courte>"}}"""

    # Provider-agnostic — caller passes the right client
    response = judge_client.chat(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"accuracy": 0, "clarity": 0, "completeness": 0, "reasoning": "parse_error"}
