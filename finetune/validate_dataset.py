"""Dependency-free schema subset and holdout-leak validator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED = {
    "sample_id", "family", "template_id", "split", "review_status",
    "source_task_id", "task_contract", "observation", "agent_state",
    "tools_schema", "candidate_snapshot", "completion", "tool_result", "provenance",
}
ALLOWED_SPLITS = {"unassigned", "train", "validation", "internal_test"}
ALLOWED_STATUS = {"draft", "reviewed", "rejected"}


def validate_sample(sample: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED - set(sample))
    if missing:
        errors.append("missing keys: " + ", ".join(missing))
    if sample.get("split") not in ALLOWED_SPLITS:
        errors.append("invalid split")
    if sample.get("review_status") not in ALLOWED_STATUS:
        errors.append("invalid review_status")
    task_id = str(sample.get("source_task_id") or "")
    serialized = json.dumps(sample, ensure_ascii=False).lower()
    if task_id.startswith("heldout_") or "development_heldout" in serialized or "final blind" in serialized:
        errors.append("held-out or blind data reference is forbidden")
    completion = sample.get("completion")
    if not isinstance(completion, dict) or not completion.get("action") or not completion.get("reason"):
        errors.append("invalid completion")
    if len(str((completion or {}).get("reason") or "")) > 160:
        errors.append("completion reason exceeds 160 characters")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    failures = []
    count = 0
    for line_number, line in enumerate(args.input.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        count += 1
        errors = validate_sample(json.loads(line))
        if errors:
            failures.append({"line": line_number, "errors": errors})
    print(json.dumps({"samples": count, "valid": count - len(failures), "failures": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
