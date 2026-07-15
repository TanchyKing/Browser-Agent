"""Full-schema, grounding, split, and holdout-leak validator."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REQUIRED = {
    "sample_id", "family", "template_id", "split", "review_status",
    "source_task_id", "task_contract", "observation", "agent_state",
    "tools_schema", "candidate_snapshot", "completion", "semantic_completion", "tool_result", "provenance",
}
ALLOWED_SPLITS = {"unassigned", "train", "validation", "internal_test"}
ALLOWED_STATUS = {"draft", "reviewed", "rejected"}
TARGET_ACTIONS = {"click", "type", "select", "extract_text", "download_file"}


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
    if isinstance(completion, dict):
        action = str(completion.get("action") or "")
        target = completion.get("target")
        if action in TARGET_ACTIONS:
            if not isinstance(target, str) or not target.strip():
                errors.append(f"{action} completion requires target")
            else:
                candidates = (sample.get("candidate_snapshot") or {}).get("selectors") or []
                grounded = {_selector_key(item) for item in candidates}
                if _selector_key(target) not in grounded:
                    errors.append("completion target is not grounded in candidate_snapshot")
        elif action in {"finish", "request_human", "refuse", "observe_page"} and target is not None:
            errors.append(f"{action} completion requires target=null")
        if action in {"type", "select"} and completion.get("value") is None:
            errors.append(f"{action} completion requires value")
        semantics = sample.get("semantic_completion")
        if not isinstance(semantics, dict) or not str(semantics.get("action_reason") or "").strip():
            errors.append("invalid semantic_completion")
        else:
            user_result = semantics.get("user_visible_result")
            if action in {"finish", "request_human", "refuse"}:
                if not isinstance(user_result, str) or not user_result.strip():
                    errors.append("terminal semantic user_visible_result is required")
                elif str(completion.get("reason") or "").strip() != user_result.strip():
                    errors.append("canonical R10e terminal reason must equal semantic user_visible_result")
            elif user_result is not None:
                errors.append("non-terminal semantic user_visible_result must be null")
            elif str(completion.get("reason") or "").strip() != str(semantics.get("action_reason") or "").strip():
                errors.append("non-terminal reason must equal semantic action_reason")
    return errors


def _selector_key(value: Any) -> str:
    text = str(value or "").strip().lower().replace('"', "'")
    return re.sub(r"\s+", "", text)


def _full_schema_errors(sample: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError as exc:  # pragma: no cover - base repo installs jsonschema
        raise RuntimeError("jsonschema is required for full dataset validation") from exc
    validator = Draft202012Validator(schema)
    return [
        f"schema {'.'.join(str(item) for item in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(sample), key=lambda item: list(item.absolute_path))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--schema", default=Path("finetune/schema/step_sample.schema.json"), type=Path)
    args = parser.parse_args()
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    failures = []
    count = 0
    sample_ids: set[str] = set()
    template_splits: dict[str, set[str]] = {}
    status_counts: dict[str, int] = {}
    for line_number, line in enumerate(args.input.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        count += 1
        sample = json.loads(line)
        errors = [*validate_sample(sample), *_full_schema_errors(sample, schema)]
        sample_id = str(sample.get("sample_id") or "")
        if sample_id in sample_ids:
            errors.append("duplicate sample_id")
        sample_ids.add(sample_id)
        template = str(sample.get("template_id") or "")
        template_splits.setdefault(template, set()).add(str(sample.get("split") or ""))
        status = str(sample.get("review_status") or "")
        status_counts[status] = status_counts.get(status, 0) + 1
        if errors:
            failures.append({"line": line_number, "errors": errors})
    leaked = sorted(template for template, splits in template_splits.items() if len(splits) != 1)
    if leaked:
        failures.append({"line": 0, "errors": ["templates cross splits: " + ", ".join(leaked)]})
    print(json.dumps({
        "samples": count,
        "valid": count - sum(1 for item in failures if item["line"] > 0),
        "unique_sample_ids": len(sample_ids),
        "review_status": dict(sorted(status_counts.items())),
        "template_split_leaks": leaked,
        "failures": failures,
    }, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
