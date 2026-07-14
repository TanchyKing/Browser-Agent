"""Evaluate browser-agent task traces.

This script accepts mock traces today and real agent traces later. It avoids
project-specific browser imports so Conversation E can be verified before the
browser and agent lanes are complete.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.runner import evaluate_trace_file
from src.eval.io import write_json
from src.experiment_config import load_experiment_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate browser-agent task traces.")
    parser.add_argument("--traces", required=True, help="Path to JSON/JSONL trace runs.")
    parser.add_argument("--browser-trace", help="Optional C-line browser JSONL step trace to merge.")
    parser.add_argument("--tasks", help="Optional task JSONL for success_check support annotation.")
    parser.add_argument("--out-json", help="Optional output JSON summary path.")
    parser.add_argument("--out-csv", help="Optional output CSV summary path.")
    parser.add_argument("--config", help="Versioned Phase 2 experiment YAML/JSON config.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_experiment_config(args.config)
    result = evaluate_trace_file(
        args.traces,
        None,
        args.out_csv,
        browser_trace_path=args.browser_trace,
        tasks_path=args.tasks,
    )
    payload = result.to_payload()
    payload["experiment"] = config.snapshot()
    if args.out_json:
        write_json(args.out_json, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
