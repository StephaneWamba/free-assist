"""
FreeAssist — QLoRA Fine-tuning with TRL SFTTrainer

Fine-tunes Mistral-7B-Instruct for support response generation
using QLoRA (4-bit quantization + LoRA adapters).

Why TRL SFTTrainer and not a custom loop?
  - Handles packing, loss masking on prompt, gradient checkpointing
  - Native integration with PEFT and bitsandbytes
  - One less thing to debug on H100

Usage:
    python train_qlora.py \
        --data_file ../../data/processed/train/conversations.jsonl \
        --output_dir ../../ml/models/qlora_mistral \
        --epochs 3
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

import mlflow

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_MODEL = os.getenv("BASE_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
MAX_SEQ_LEN = 2048

LORA_CONFIG = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,                    # rank — balance between capacity and compute
    lora_alpha=32,           # scaling factor
    lora_dropout=0.05,
    bias="none",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
)

BNBCONFIG = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",      # NF4 is optimal for normally-distributed weights
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,  # nested quantization — saves ~0.4 bits/param
)


# ---------------------------------------------------------------------------
# Data formatting
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "Tu es un assistant expert du support technique Iliad-Free. "
    "Tu aides les agents de support à rédiger des réponses claires, professionnelles et précises."
)


def format_conversation(record: dict) -> str:
    """
    Format a conversation into Mistral instruction format:
    [INST] user_context [/INST] agent_response
    """
    turns = record.get("turns", [])
    if len(turns) < 2:
        return ""

    user_context = " | ".join(
        t["content"] for t in turns if t["role"] == "user"
    )
    last_agent_response = next(
        (t["content"] for t in reversed(turns) if t["role"] == "agent"), ""
    )

    if not last_agent_response:
        return ""

    return (
        f"<s>[INST] <<SYS>>\n{_SYSTEM_PROMPT}\n<</SYS>>\n\n"
        f"Ticket client : {user_context} [/INST] "
        f"{last_agent_response} </s>"
    )


def load_dataset_from_jsonl(path: str | Path) -> Dataset:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            text = format_conversation(record)
            if text:
                records.append({"text": text, "intent": record.get("intent", "OTHER")})

    print(f"Loaded {len(records)} training examples from {path}")
    return Dataset.from_list(records)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train(
    data_file: str,
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 4,
    gradient_accumulation_steps: int = 4,  # effective batch = 16 on single H100
    learning_rate: float = 2e-4,
    seed: int = 42,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset_from_jsonl(data_file)

    print(f"Loading {BASE_MODEL} in 4-bit (QLoRA)…")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=BNBCONFIG,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False  # required for gradient checkpointing

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    sft_config = SFTConfig(
        output_dir=str(output_path),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",  # memory-efficient optimizer for QLoRA
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        bf16=True,
        logging_steps=10,
        save_strategy="epoch",
        max_seq_length=MAX_SEQ_LEN,
        dataset_text_field="text",
        packing=True,              # pack short sequences — maximizes GPU utilization
        seed=seed,
        report_to=["mlflow"],
    )

    mlflow.set_experiment("freeassist-qlora-mistral")
    with mlflow.start_run(run_name=f"qlora-ep{epochs}-r{LORA_CONFIG.r}"):
        mlflow.log_params({
            "base_model": BASE_MODEL,
            "lora_rank": LORA_CONFIG.r,
            "lora_alpha": LORA_CONFIG.lora_alpha,
            "epochs": epochs,
            "batch_size": batch_size,
            "grad_accum": gradient_accumulation_steps,
            "lr": learning_rate,
            "train_samples": len(dataset),
            "quant": "4bit-nf4-double",
        })

        trainer = SFTTrainer(
            model=model,
            args=sft_config,
            train_dataset=dataset,
            peft_config=LORA_CONFIG,
            tokenizer=tokenizer,
        )

        print("Starting QLoRA fine-tuning…")
        trainer.train()

        # Save LoRA adapters (not full model — saves disk space)
        adapter_path = output_path / "lora_adapters"
        trainer.model.save_pretrained(str(adapter_path))
        tokenizer.save_pretrained(str(adapter_path))
        print(f"LoRA adapters saved to {adapter_path}")
        mlflow.log_artifact(str(adapter_path))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning of Mistral-7B for FreeAssist")
    parser.add_argument("--data_file", required=True)
    parser.add_argument("--output_dir", default="../../ml/models/qlora_mistral")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train(
        data_file=args.data_file,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
