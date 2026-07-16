"""CORRECTION-2 Gate 2: offline, full-GPU QLoRA three-step probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any


SEED = 42
MICRO_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 8
FORMAL_SCHEDULER_STEPS = 500
PROBE_OPTIMIZER_STEPS = 3
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def _normalized_device(value: Any) -> str:
    if isinstance(value, int):
        return f"cuda:{value}"
    text = str(value).lower()
    if text.isdigit():
        return f"cuda:{text}"
    return text


def assert_fully_gpu_resident(device_map: dict[str, Any] | None) -> dict[str, str]:
    """Return a serializable map or fail if any module is not CUDA-resident."""

    if not device_map:
        raise RuntimeError("hf_device_map is missing or empty")
    normalized = {name: _normalized_device(device) for name, device in device_map.items()}
    forbidden = {name: device for name, device in normalized.items() if device in {"cpu", "disk"}}
    non_cuda = {name: device for name, device in normalized.items() if not device.startswith("cuda:")}
    if forbidden:
        raise RuntimeError(f"CPU/disk offload detected: {forbidden}")
    if non_cuda:
        raise RuntimeError(f"Non-CUDA device assignment detected: {non_cuda}")
    return normalized


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--expected-dataset-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--optimizer-steps", type=int, default=PROBE_OPTIMIZER_STEPS)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=GRADIENT_ACCUMULATION_STEPS)
    return parser.parse_args()


def _run(args: argparse.Namespace) -> int:
    if os.environ.get("HF_HUB_OFFLINE") != "1":
        raise RuntimeError("HF_HUB_OFFLINE=1 is required")
    if os.environ.get("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("TRANSFORMERS_OFFLINE=1 is required")
    if args.max_length <= 0 or args.optimizer_steps != PROBE_OPTIMIZER_STEPS:
        raise ValueError("Gate 2 requires max_length > 0 and exactly 3 optimizer steps")
    if args.gradient_accumulation_steps != GRADIENT_ACCUMULATION_STEPS:
        raise ValueError("Gate 2 requires the frozen gradient accumulation value 8")
    if args.learning_rate != 2e-4:
        raise ValueError("Gate 2 requires the frozen learning rate 2e-4")
    model_path = args.model_path.resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"Local model snapshot is missing: {model_path}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty probe output: {args.output_dir}")

    dataset_bytes = args.dataset.read_bytes()
    dataset_sha256 = hashlib.sha256(dataset_bytes).hexdigest()
    if dataset_sha256 != args.expected_dataset_sha256.lower():
        raise ValueError(
            f"Dataset digest mismatch: expected {args.expected_dataset_sha256}, got {dataset_sha256}"
        )
    rows = [json.loads(line) for line in dataset_bytes.decode("utf-8").splitlines() if line.strip()]
    train_rows = [row for row in rows if row.get("split") == "train"]
    if len(train_rows) != 486:
        raise ValueError(f"Expected 486 frozen training rows, got {len(train_rows)}")

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, get_scheduler

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for Gate 2")

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

    tokenizer = AutoTokenizer.from_pretrained(
        str(model_path),
        local_files_only=True,
        use_fast=True,
    )
    tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token
    tokenizer.padding_side = "right"

    def collate(texts: list[str]) -> dict[str, Any]:
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
        batch_size=MICRO_BATCH_SIZE,
        shuffle=True,
        generator=train_generator,
        collate_fn=collate,
        num_workers=0,
    )

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    marker = args.output_dir / "probe_started.json"
    _write_json(
        marker,
        {
            "status": "started",
            "preflight_only": True,
            "offline": True,
            "model_path": str(model_path),
            "dataset_sha256": dataset_sha256,
            "max_length": args.max_length,
            "optimizer_steps": args.optimizer_steps,
            "micro_batch_size": MICRO_BATCH_SIZE,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "learning_rate": args.learning_rate,
        },
    )

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        local_files_only=True,
        quantization_config=quantization,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    torch.cuda.synchronize()
    device_map = assert_fully_gpu_resident(getattr(model, "hf_device_map", None))
    memory_after_base_load = {
        "allocated_bytes": torch.cuda.memory_allocated(),
        "reserved_bytes": torch.cuda.memory_reserved(),
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
    }

    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(
        model,
        LoraConfig(
            r=LORA_R,
            lora_alpha=LORA_ALPHA,
            lora_dropout=LORA_DROPOUT,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules="all-linear",
        ),
    )
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.train()

    input_device = model.get_input_embeddings().weight.device
    if input_device.type != "cuda":
        raise RuntimeError(f"Input embeddings are not on CUDA: {input_device}")
    trainable_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable_parameters, lr=args.learning_rate, weight_decay=0.0)
    scheduler = get_scheduler(
        "linear",
        optimizer=optimizer,
        num_warmup_steps=0,
        num_training_steps=FORMAL_SCHEDULER_STEPS,
    )
    trainable_count = sum(parameter.numel() for parameter in trainable_parameters)
    logs_path = args.output_dir / "probe_log.jsonl"

    def move_to_device(batch: dict[str, Any]) -> dict[str, Any]:
        return {name: tensor.to(input_device) for name, tensor in batch.items()}

    optimizer.zero_grad(set_to_none=True)
    train_iterator = iter(train_loader)
    peak_sequence_tokens = 0
    final_loss = math.nan
    for step in range(1, args.optimizer_steps + 1):
        micro_losses: list[float] = []
        micro_token_lengths: list[int] = []
        for _ in range(args.gradient_accumulation_steps):
            try:
                batch = next(train_iterator)
            except StopIteration:
                train_iterator = iter(train_loader)
                batch = next(train_iterator)
            lengths = batch["attention_mask"].sum(dim=1)
            micro_token_lengths.extend(int(value) for value in lengths.tolist())
            peak_sequence_tokens = max(peak_sequence_tokens, max(micro_token_lengths))
            batch = move_to_device(batch)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                loss = model(**batch, use_cache=False).loss
            micro_losses.append(float(loss.detach().cpu()))
            (loss / args.gradient_accumulation_steps).backward()

        grad_norm = torch.nn.utils.clip_grad_norm_(trainable_parameters, 1.0)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        final_loss = sum(micro_losses) / len(micro_losses)
        record = {
            "event": "probe_train",
            "step": step,
            "loss": final_loss,
            "grad_norm": float(grad_norm.detach().cpu()),
            "learning_rate": scheduler.get_last_lr()[0],
            "micro_token_lengths": micro_token_lengths,
            "memory_allocated_bytes": torch.cuda.memory_allocated(),
            "memory_reserved_bytes": torch.cuda.memory_reserved(),
            "peak_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
            "elapsed_seconds": round(time.monotonic() - started, 2),
        }
        _append_jsonl(logs_path, record)
        print(json.dumps(record), flush=True)

    elapsed_seconds = time.monotonic() - started
    result = {
        "status": "passed",
        "preflight_only": True,
        "offline": True,
        "model_path": str(model_path),
        "dataset_sha256": dataset_sha256,
        "hf_device_map": device_map,
        "no_cpu_or_disk_offload": True,
        "optimizer_steps": args.optimizer_steps,
        "micro_batches": args.optimizer_steps * args.gradient_accumulation_steps,
        "max_length": args.max_length,
        "maximum_observed_sequence_tokens": peak_sequence_tokens,
        "micro_batch_size": MICRO_BATCH_SIZE,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.learning_rate,
        "formal_scheduler_steps": FORMAL_SCHEDULER_STEPS,
        "quantization": {
            "load_in_4bit": True,
            "type": "nf4",
            "compute_dtype": "bfloat16",
            "double_quant": True,
        },
        "lora": {
            "r": LORA_R,
            "alpha": LORA_ALPHA,
            "dropout": LORA_DROPOUT,
            "bias": "none",
            "target_modules": "all-linear",
        },
        "optimizer": "torch.optim.AdamW",
        "weight_decay": 0.0,
        "gradient_checkpointing": True,
        "trainable_parameters": trainable_count,
        "final_probe_loss": final_loss,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "memory_after_base_load": memory_after_base_load,
        "peak_gpu_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_gpu_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
        "gpu": torch.cuda.get_device_name(0),
        "torch_cuda": torch.version.cuda,
    }
    _write_json(args.output_dir / "probe_result.json", result)
    print(json.dumps({"event": "probe_complete", **result}), flush=True)
    return 0


def main() -> int:
    args = _parse_args()
    try:
        return _run(args)
    except BaseException as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure: dict[str, Any] = {
            "status": "failed",
            "preflight_only": True,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "oom": type(exc).__name__ == "OutOfMemoryError" or "out of memory" in str(exc).lower(),
        }
        try:
            import torch

            if torch.cuda.is_available():
                failure.update(
                    {
                        "memory_allocated_bytes": torch.cuda.memory_allocated(),
                        "memory_reserved_bytes": torch.cuda.memory_reserved(),
                        "peak_gpu_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
                        "peak_gpu_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
                    }
                )
        except Exception:
            pass
        _write_json(args.output_dir / "probe_failure.json", failure)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
