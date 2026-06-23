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
    parser.add_argument("--task-id", action="append", dest="task_ids", help="Task id to run; repeatable. Defaults to all tasks.")
    parser.add_argument("--out", default="artifacts/traces/task_suite_mock_runs.json")
    parser.add_argument("--trace-dir", default="artifacts/traces/task_suite")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task_ids = args.task_ids or task_ids_from_file()
    runs = []
    trace_dir = Path(args.trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    for task_id in task_ids:
        read_task(task_id)
        safe_name = task_id.replace("/", "_")
        run_out = trace_dir / f"{safe_name}_{args.backend}_run.json"
        trace_out = trace_dir / f"{safe_name}_{args.backend}_browser_trace.jsonl"
        run = run_demo(task_id, trace_out, run_out, backend=args.backend)
        runs.append(run)
        print(f"{task_id}: {run['status']} steps={len(run.get('steps') or [])}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"runs": runs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(run.get("status") == "success" for run in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
