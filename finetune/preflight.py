"""Fail-fast environment, CUDA, disk, and package preflight; performs no training."""

from __future__ import annotations

import importlib.metadata
import json
import shutil
from pathlib import Path


PACKAGES = ["torch", "transformers", "trl", "peft", "accelerate", "bitsandbytes", "datasets"]


def main() -> int:
    report = {"packages": {}, "disk_free_gb": round(shutil.disk_usage(Path.cwd()).free / 2**30, 2)}
    missing = []
    for package in PACKAGES:
        try:
            report["packages"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report["packages"][package] = None
            missing.append(package)
    if not missing:
        import torch
        report["torch_cuda"] = torch.version.cuda
        report["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            report["gpu"] = props.name
            report["vram_gb"] = round(props.total_memory / 2**30, 2)
    report["ready"] = not missing and bool(report.get("cuda_available")) and report["disk_free_gb"] >= 30
    report["missing"] = missing
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
