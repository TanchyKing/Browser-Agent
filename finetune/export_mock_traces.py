"""Export reconstructable A0 run traces into draft step-level SFT samples."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FAILED_PHASE1_BUSINESS = {
    "jobs_remote_mid_data_scientist",
    "invoice_research_vendor",
    "inventory_high_priority_low_stock",
    "download_q2_operations",
    "copy_project_code",
    "benefits_premium_two_dependents",
}
SAFETY_PREFIXES = ("resist_prompt_injection_", "sensitive_email_")


def load_task_families(path: Path) -> dict[str, str]:
    families: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            task = json.loads(line)
            families[str(task["task_id"])] = str(task.get("category") or "unknown")
    return families


def export_samples(runs_path: Path, tasks_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(runs_path.read_text(encoding="utf-8"))
    runs = payload.get("runs") if isinstance(payload, dict) else payload
    if not isinstance(runs, list):
        raise ValueError("Run artifact must contain a runs list")
    families = load_task_families(tasks_path)
    samples: list[dict[str, Any]] = []
    for run in runs:
        task_id = str(run.get("task_id"))
        for step in run.get("steps") or []:
            attempts = step.get("llm_attempts") or []
            if not attempts or not step.get("action_type"):
                continue
            request = attempts[-1].get("request") or {}
            identity = f"{run.get('run_id')}:{step.get('step_index')}:{task_id}"
            samples.append(
                {
                    "sample_id": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                    "family": families.get(task_id, "unknown"),
                    "template_id": families.get(task_id, task_id),
                    "split": "unassigned",
                    "review_status": "draft",
                    "source_task_id": task_id,
                    "task_contract": str(request.get("task_preview") or ""),
                    "observation": str(request.get("observation_preview") or ""),
                    "agent_state": step.get("state_before"),
                    "tools_schema": request.get("action_schema") or {},
                    "candidate_snapshot": request.get("candidate_snapshot"),
                    "completion": {
                        "action": step.get("action_type"),
                        "target": step.get("target"),
                        "value": step.get("value"),
                        "reason": step.get("reason") or "correct next action",
                        "risk_level": step.get("risk_level") or "low",
                        "metadata": step.get("action_metadata") or {},
                    },
                    "tool_result": step.get("tool_result") or {},
                    "safety_labels": ["safe_behavior"] if task_id.startswith(SAFETY_PREFIXES) else [],
                    "correction_for": "phase1_qwen_failure" if task_id in FAILED_PHASE1_BUSINESS else None,
                    "provenance": {
                        "run_id": str(run.get("run_id") or ""),
                        "step_index": int(step.get("step_index") or 0),
                        "config_sha256": (run.get("experiment") or {}).get("sha256"),
                        "source_artifact": str(runs_path),
                    },
                }
            )
    return samples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--tasks", default="tasks/offline_tasks.jsonl", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    samples = export_samples(args.runs, args.tasks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample in samples),
        encoding="utf-8",
    )
    print(json.dumps({"samples": len(samples), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
