"""Input/output helpers for evaluation traces and summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def read_runs(path: str | Path) -> list[dict[str, Any]]:
    """Read runs from a JSON array, single JSON object, or JSONL file."""

    trace_path = Path(path)
    text = trace_path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if trace_path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    payload = json.loads(text)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("runs"), list):
            return payload["runs"]
        return [payload]
    raise ValueError(f"Unsupported run payload in {trace_path}")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_summary_csv(path: str | Path, summary: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flat: dict[str, Any] = {}
    for key, value in summary.items():
        if isinstance(value, dict):
            flat.update({f"{key}.{nested_key}": nested for nested_key, nested in value.items()})
        else:
            flat[key] = value
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat.keys()))
        writer.writeheader()
        writer.writerow(flat)
