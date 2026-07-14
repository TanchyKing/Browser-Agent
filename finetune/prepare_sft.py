"""Convert reviewed step samples into short prompt/completion records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--include-draft", action="store_true")
    args = parser.parse_args()
    output = []
    for line in args.input.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sample = json.loads(line)
        if sample["review_status"] != "reviewed" and not args.include_draft:
            continue
        prompt = "\n\n".join(
            [
                "Task contract:\n" + sample["task_contract"],
                "Observation:\n" + sample["observation"],
                "Agent state:\n" + json.dumps(sample["agent_state"], ensure_ascii=False, sort_keys=True),
                "Action schema:\n" + json.dumps(sample["tools_schema"], ensure_ascii=False, sort_keys=True),
            ]
        )
        output.append({"text": prompt + "\n\nAssistant action:\n" + json.dumps(sample["completion"], ensure_ascii=False, separators=(",", ":")), "split": sample["split"], "sample_id": sample["sample_id"]})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in output), encoding="utf-8")
    print(json.dumps({"records": len(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
