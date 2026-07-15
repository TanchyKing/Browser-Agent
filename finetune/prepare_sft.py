"""Convert reviewed step samples into short prompt/completion records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finetune.interface_rendering import INTERFACES, render_sample


def prepare_records(
    samples: list[dict],
    *,
    include_draft: bool = False,
    interface: str = "r10e",
) -> list[dict]:
    output = []
    for raw_sample in samples:
        if raw_sample["review_status"] != "reviewed" and not include_draft:
            continue
        sample = render_sample(raw_sample, interface)
        prompt = "\n\n".join(
            [
                "Task contract:\n" + sample["task_contract"],
                "Observation:\n" + sample["observation"],
                "Agent state:\n" + json.dumps(sample["agent_state"], ensure_ascii=False, sort_keys=True),
                "Action schema:\n" + json.dumps(sample["tools_schema"], ensure_ascii=False, sort_keys=True),
            ]
        )
        output.append(
            {
                "text": prompt
                + "\n\nAssistant action:\n"
                + json.dumps(sample["completion"], ensure_ascii=False, separators=(",", ":")),
                "split": sample["split"],
                "sample_id": sample["sample_id"],
                "interface": interface,
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--include-draft", action="store_true")
    parser.add_argument("--interface", choices=sorted(INTERFACES), default="r10e")
    args = parser.parse_args()
    samples = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    output = prepare_records(samples, include_draft=args.include_draft, interface=args.interface)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in output), encoding="utf-8")
    print(json.dumps({"records": len(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
