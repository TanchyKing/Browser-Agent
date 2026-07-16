"""Deterministic QLoRA SFT entrypoint. Running this file is a GPU Gate operation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import random
import time
from pathlib import Path
from typing import Any


SEED = 42
GRADIENT_ACCUMULATION_STEPS = 8
EVAL_STEPS = 50
SAVE_STEPS = 50


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-8B")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        get_scheduler,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for this QLoRA gate")
    if args.max_steps <= 0 or args.max_length <= 0:
        raise ValueError("max-steps and max-length must be positive")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {args.output_dir}")

    dataset_bytes = args.dataset.read_bytes()
    rows = [json.loads(line) for line in dataset_bytes.decode("utf-8").splitlines() if line.strip()]
    train_rows = [row for row in rows if row.get("split") == "train"]
    validation_rows = [row for row in rows if row.get("split") == "validation"]
    internal_test_rows = [row for row in rows if row.get("split") == "internal_test"]
    if not train_rows or not validation_rows:
        raise ValueError("Dataset must contain train and validation records")
    if any(not isinstance(row.get("text"), str) or not row["text"] for row in rows):
        raise ValueError("Every dataset record must contain non-empty text")

    random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)

    class TextDataset(Dataset):
        def __init__(self, values: list[dict[str, Any]]) -> None:
            self.values = values

        def __len__(self) -> int:
            return len(self.values)

        def __getitem__(self, index: int) -> str:
            return self.values[index]["text"]

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        revision=args.revision,
        use_fast=True,
    )
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    tokenizer.padding_side = "right"

    def collate(texts: list[str]) -> dict[str, torch.Tensor]:
        batch = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=args.max_length,
            return_tensors="pt",
        )
        labels = batch["input_ids"].clone()
        labels[batch["attention_mask"] == 0] = -100
        batch["labels"] = labels
        return batch

    train_generator = torch.Generator().manual_seed(SEED)
    train_loader = DataLoader(
        TextDataset(train_rows),
        batch_size=1,
        shuffle=True,
        generator=train_generator,
        collate_fn=collate,
        num_workers=0,
    )
    validation_loader = DataLoader(
        TextDataset(validation_rows),
        batch_size=1,
        shuffle=False,
        collate_fn=collate,
        num_workers=0,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        revision=args.revision,
        quantization_config=quantization,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )
    model = get_peft_model(model, lora)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.train()

    input_device = model.get_input_embeddings().weight.device
    trainable_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable_parameters, lr=args.learning_rate, weight_decay=0.0)
    scheduler = get_scheduler(
        "linear",
        optimizer=optimizer,
        num_warmup_steps=0,
        num_training_steps=args.max_steps,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    logs_path = args.output_dir / "log_history.jsonl"
    run_config = {
        "implementation": "manual_torch_peft_no_pyarrow_v1",
        "model": args.model,
        "revision": args.revision,
        "dataset": str(args.dataset),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "dataset_counts": {
            "train": len(train_rows),
            "validation": len(validation_rows),
            "internal_test_excluded": len(internal_test_rows),
        },
        "max_length": args.max_length,
        "max_steps": args.max_steps,
        "learning_rate": args.learning_rate,
        "lr_scheduler": "linear",
        "warmup_steps": 0,
        "weight_decay": 0.0,
        "max_grad_norm": 1.0,
        "seed": SEED,
        "quantization": {
            "load_in_4bit": True,
            "type": "nf4",
            "compute_dtype": "bfloat16",
            "double_quant": True,
        },
        "lora": {
            "r": 16,
            "alpha": 32,
            "dropout": 0.05,
            "bias": "none",
            "target_modules": "all-linear",
        },
        "batching": {
            "per_device_train_batch_size": 1,
            "per_device_eval_batch_size": 1,
            "gradient_accumulation_steps": GRADIENT_ACCUMULATION_STEPS,
            "gradient_checkpointing": True,
        },
        "evaluation": {
            "eval_steps": EVAL_STEPS,
            "also_evaluate_at_final_step": True,
        },
        "saving": {"save_steps": SAVE_STEPS},
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("torch", "transformers", "peft", "accelerate", "bitsandbytes")
        },
        "torch_cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
    }
    _write_json(args.output_dir / "run_config.json", run_config)

    def move_to_device(batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        return {name: tensor.to(input_device) for name, tensor in batch.items()}

    @torch.no_grad()
    def evaluate(step: int) -> float:
        model.eval()
        losses: list[float] = []
        for batch in validation_loader:
            batch = move_to_device(batch)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                loss = model(**batch, use_cache=False).loss
            losses.append(float(loss.detach().cpu()))
        model.train()
        mean_loss = sum(losses) / len(losses)
        record = {"event": "eval", "step": step, "eval_loss": mean_loss}
        _append_jsonl(logs_path, record)
        print(json.dumps(record), flush=True)
        return mean_loss

    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    optimizer.zero_grad(set_to_none=True)
    train_iterator = iter(train_loader)
    final_eval_loss: float | None = None
    last_train_loss = math.nan

    for step in range(1, args.max_steps + 1):
        micro_losses: list[float] = []
        for _ in range(GRADIENT_ACCUMULATION_STEPS):
            try:
                batch = next(train_iterator)
            except StopIteration:
                train_iterator = iter(train_loader)
                batch = next(train_iterator)
            batch = move_to_device(batch)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                loss = model(**batch, use_cache=False).loss
            micro_losses.append(float(loss.detach().cpu()))
            (loss / GRADIENT_ACCUMULATION_STEPS).backward()

        grad_norm = torch.nn.utils.clip_grad_norm_(trainable_parameters, 1.0)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        last_train_loss = sum(micro_losses) / len(micro_losses)
        train_record = {
            "event": "train",
            "step": step,
            "loss": last_train_loss,
            "grad_norm": float(grad_norm.detach().cpu()) if isinstance(grad_norm, torch.Tensor) else float(grad_norm),
            "learning_rate": scheduler.get_last_lr()[0],
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }
        _append_jsonl(logs_path, train_record)
        print(json.dumps(train_record), flush=True)

        if step % SAVE_STEPS == 0:
            checkpoint_dir = args.output_dir / f"checkpoint-{step}"
            model.save_pretrained(checkpoint_dir / "adapter")
            tokenizer.save_pretrained(checkpoint_dir / "adapter")
            torch.save(
                {"step": step, "optimizer": optimizer.state_dict(), "scheduler": scheduler.state_dict()},
                checkpoint_dir / "training_state.pt",
            )
        if step % EVAL_STEPS == 0 or step == args.max_steps:
            final_eval_loss = evaluate(step)

    adapter_dir = args.output_dir / "adapter"
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    elapsed_seconds = time.monotonic() - started
    metrics = {
        "train_steps": args.max_steps,
        "train_loss_last_step": last_train_loss,
        "eval_loss_final": final_eval_loss,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "samples_per_second": round(
            (args.max_steps * GRADIENT_ACCUMULATION_STEPS) / elapsed_seconds,
            6,
        ),
        "max_gpu_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
        "max_gpu_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
    }
    _write_json(args.output_dir / "train_metrics.json", metrics)
    print(json.dumps({"event": "complete", **metrics}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
