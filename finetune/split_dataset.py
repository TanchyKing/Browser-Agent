"""Assign whole task families to splits and reject template leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def assign_split(template_id: str) -> str:
    bucket = int(hashlib.sha256(template_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket < 7:
        return "train"
    if bucket < 9:
        return "validation"
    return "internal_test"


def split_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assignments: dict[str, str] = {}
    for sample in samples:
        template = str(sample["template_id"])
        assignments.setdefault(template, assign_split(template))
        sample["split"] = assignments[template]
    seen: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        seen[str(sample["template_id"])].add(str(sample["split"]))
    leaked = {template: splits for template, splits in seen.items() if len(splits) != 1}
    if leaked:
        raise ValueError(f"Template leakage across splits: {leaked}")
    return samples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    samples = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    split_samples(samples)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in samples), encoding="utf-8")
    counts: dict[str, int] = defaultdict(int)
    for sample in samples:
        counts[str(sample["split"])] += 1
    print(json.dumps(dict(sorted(counts.items()))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
