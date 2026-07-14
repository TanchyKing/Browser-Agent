"""Run a set of offline tasks and write one combined run artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_demo import read_task, run_demo
from src.experiment_config import load_experiment_config, load_suite_manifest


def task_ids_from_file() -> list[str]:
    task_path = ROOT / "tasks" / "offline_tasks.jsonl"
    task_ids: list[str] = []
    for line in task_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            task_ids.append(str(json.loads(line)["task_id"]))
    return task_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline browser-agent task suite.")
    parser.add_argument("--backend", choices=["mock", "ollama"], default="mock")
    suite_group = parser.add_mutually_exclusive_group()
    suite_group.add_argument("--task-id", action="append", dest="task_ids", help="Task id to run; repeatable. Defaults to all tasks.")
    suite_group.add_argument("--suite-manifest", help="Frozen JSON suite manifest.")
    parser.add_argument("--config", help="Versioned Phase 2 experiment YAML/JSON config.")
    parser.add_argument("--out", default="artifacts/traces/task_suite_mock_runs.json")
    parser.add_argument("--trace-dir", default="artifacts/traces/task_suite")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_experiment_config(args.config)
    manifest = load_suite_manifest(args.suite_manifest) if args.suite_manifest else None
    task_ids = list(manifest.task_ids) if manifest else (args.task_ids or task_ids_from_file())
    runs = []
    trace_dir = Path(args.trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    for task_id in task_ids:
        read_task(task_id, config.evaluator.task_file_path, config.evaluator.task_overrides_path)
        safe_name = task_id.replace("/", "_")
        run_out = trace_dir / f"{safe_name}_{args.backend}_run.json"
        trace_out = trace_dir / f"{safe_name}_{args.backend}_browser_trace.jsonl"
        run = run_demo(task_id, trace_out, run_out, backend=args.backend, config=config)
        runs.append(run)
        print(f"{task_id}: {run['status']} steps={len(run.get('steps') or [])}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    suite_snapshot = (
        manifest.snapshot()
        if manifest
        else {"suite_id": "ad-hoc", "task_ids": task_ids, "source_path": None, "sha256": None}
    )
    out_path.write_text(
        json.dumps(
            {"experiment": config.snapshot(), "suite": suite_snapshot, "runs": runs},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if all(run.get("status") == "success" for run in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
