"""Fail-fast environment, CUDA, disk, and import preflight; performs no training."""

from __future__ import annotations

import importlib.metadata
import json
import shutil
from pathlib import Path


PACKAGES = ["torch", "transformers", "peft", "accelerate", "bitsandbytes", "safetensors", "sentencepiece"]


def main() -> int:
    report = {"packages": {}, "imports": {}, "disk_free_gb": round(shutil.disk_usage(Path.cwd()).free / 2**30, 2)}
    missing = []
    for package in PACKAGES:
        try:
            report["packages"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report["packages"][package] = None
            missing.append(package)

    import_error = None
    if not missing:
        try:
            import bitsandbytes  # noqa: F401
            import torch
            from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # noqa: F401
            from transformers import (  # noqa: F401
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
                get_scheduler,
            )
            report["imports"]["training_stack"] = "ok"
            report["torch_cuda"] = torch.version.cuda
            report["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                report["gpu"] = props.name
                report["vram_gb"] = round(props.total_memory / 2**30, 2)
                report["compute_capability"] = f"{props.major}.{props.minor}"
                left = torch.randn((16, 16), device="cuda", dtype=torch.bfloat16)
                right = torch.randn((16, 16), device="cuda", dtype=torch.bfloat16)
                result = left @ right
                torch.cuda.synchronize()
                report["bf16_cuda_matmul"] = bool(torch.isfinite(result).all().item())
        except Exception as exc:  # preflight must serialize the exact import/runtime failure
            import_error = f"{type(exc).__name__}: {exc}"
            report["imports"]["training_stack"] = import_error

    report["ready"] = (
        not missing
        and import_error is None
        and bool(report.get("cuda_available"))
        and bool(report.get("bf16_cuda_matmul"))
        and report["disk_free_gb"] >= 30
    )
    report["missing"] = missing
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
