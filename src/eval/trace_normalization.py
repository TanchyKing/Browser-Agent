"""Normalize run artifacts and browser step JSONL into evaluation runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .error_analysis import classify_error_type
from .io import read_runs


def is_browser_step(record: dict[str, Any]) -> bool:
    return "ok" in record and "action" in record and "step_index" in record


def normalize_browser_step(record: dict[str, Any], *, index: int | None = None) -> dict[str, Any]:
    action = record.get("action") or {}
    action_type = action.get("name") or record.get("action_type") or "unknown"
    error = record.get("error")
    error_type = record.get("error_type") or classify_error_type(
        error,
        action_type=str(action_type),
        ok=bool(record.get("ok", False)),
    )
    return {
        "step_index": record.get("step_index", index),
        "action_type": action_type,
        "selector": action.get("selector"),
        "valid_action": error_type != "unsupported_action",
        "execution_ok": bool(record.get("ok", False)),
        "policy_blocked": bool(record.get("policy_blocked", False)),
        "safety_violation": bool(record.get("safety_violation", False)),
        "error_type": error_type,
        "error": error,
        "extracted_text": record.get("extracted_text"),
        "download_path": record.get("download_path"),
        "metadata": record.get("metadata") or {},
    }


def browser_steps_to_runs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for idx, record in enumerate(records):
        run_id = str(record.get("run_id") or "browser-trace")
        grouped.setdefault(run_id, []).append(normalize_browser_step(record, index=idx))

    runs: list[dict[str, Any]] = []
    for run_id, steps in grouped.items():
        status = "success" if all(step.get("execution_ok", False) for step in steps) else "failed"
        runs.append(
            {
                "task_id": "browser_trace",
                "run_id": run_id,
                "status": status,
                "run_source": "browser_trace",
                "steps": steps,
                "errors": [],
            }
        )
    return runs


def load_browser_trace(path: str | Path) -> list[dict[str, Any]]:
    trace_path = Path(path)
    records = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [record for record in records if isinstance(record, dict)]


def merge_browser_trace_steps(run: dict[str, Any], browser_records: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(run)
    run_id = run.get("run_id")
    scoped_records = [
        record for record in browser_records
        if not run_id or not record.get("run_id") or str(record.get("run_id")) == str(run_id)
    ]
    browser_steps = [normalize_browser_step(record, index=idx) for idx, record in enumerate(scoped_records)]
    existing_steps = list(merged.get("steps") or [])
    if not existing_steps:
        merged["steps"] = browser_steps
        if browser_steps and any(not step.get("execution_ok", True) for step in browser_steps):
            merged.setdefault("status", "failed")
        return merged

    browser_by_step_index = {
        step.get("step_index"): step
        for step in browser_steps
        if step.get("step_index") is not None
    }
    for idx, existing in enumerate(existing_steps):
        step_index = existing.get("step_index")
        browser = browser_by_step_index.get(step_index)
        if browser is None:
            browser = browser_steps[idx] if step_index is None and idx < len(browser_steps) else None
        if browser is None:
            continue
        if "execution_ok" in browser:
            existing["execution_ok"] = browser.get("execution_ok")
        if browser.get("policy_blocked"):
            existing["policy_blocked"] = browser.get("policy_blocked")
        if browser.get("selector"):
            existing["selector"] = browser.get("selector")
        if browser.get("error"):
            existing["error"] = browser["error"]
        if browser.get("error_type") and _browser_error_should_override(existing):
            existing["error_type"] = browser["error_type"]
        if browser.get("download_path"):
            existing["download_path"] = browser["download_path"]
        if browser.get("extracted_text"):
            existing["extracted_text"] = browser["extracted_text"]
    merged["steps"] = existing_steps
    return merged


def _browser_error_should_override(existing_step: dict[str, Any]) -> bool:
    """Browser traces are authoritative for execution errors, not safety blocks."""

    if bool(existing_step.get("policy_blocked", False)) or bool(existing_step.get("safety_violation", False)):
        return False
    return str(existing_step.get("error_type") or "") not in {
        "forbidden_action",
        "safety_blocked",
        "needs_user_confirmation",
    } or existing_step.get("execution_ok") is False


def _resolve_trace_path(raw_path: str, source_path: Path) -> Path | None:
    candidate = Path(raw_path)
    if candidate.is_file():
        return candidate
    relative_to_source = source_path.parent / candidate
    if relative_to_source.is_file():
        return relative_to_source
    relative_to_cwd = Path.cwd() / candidate
    if relative_to_cwd.is_file():
        return relative_to_cwd
    return None


def normalize_runs_from_path(
    path: str | Path,
    *,
    browser_trace_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    source_path = Path(path)
    records = read_runs(source_path)
    if records and all(is_browser_step(record) for record in records):
        return browser_steps_to_runs(records)

    explicit_browser_records = load_browser_trace(browser_trace_path) if browser_trace_path else None
    normalized: list[dict[str, Any]] = []
    for run in records:
        merged = dict(run)
        records_to_merge = explicit_browser_records
        if records_to_merge is None:
            trace_ref = (merged.get("artifacts") or {}).get("browser_trace")
            trace_path = _resolve_trace_path(str(trace_ref), source_path) if trace_ref else None
            records_to_merge = load_browser_trace(trace_path) if trace_path else None
        if records_to_merge:
            merged = merge_browser_trace_steps(merged, records_to_merge)
        normalized.append(merged)
    return normalized
