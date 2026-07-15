"""Apply explicit human review decisions to a separate dataset file."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ALLOWED_DECISIONS = {"", "approve", "reject", "modify"}


def load_queue(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    decisions: dict[str, dict[str, str]] = {}
    for line_number, row in enumerate(rows, start=2):
        sample_id = str(row.get("sample_id") or "").strip()
        decision = str(row.get("decision") or "").strip().lower()
        if not sample_id or sample_id in decisions:
            raise ValueError(f"review queue line {line_number}: missing or duplicate sample_id")
        if decision not in ALLOWED_DECISIONS:
            raise ValueError(f"review queue line {line_number}: invalid decision {decision!r}")
        if decision == "approve" and not (row.get("reviewer") and row.get("reviewed_at")):
            raise ValueError(f"review queue line {line_number}: approve requires reviewer and reviewed_at")
        if decision in {"reject", "modify"} and not str(row.get("required_changes") or "").strip():
            raise ValueError(f"review queue line {line_number}: {decision} requires required_changes")
        decisions[sample_id] = row
    return decisions


def apply_decisions(dataset: list[dict], decisions: dict[str, dict[str, str]]) -> list[dict]:
    dataset_ids = {str(item.get("sample_id") or "") for item in dataset}
    if set(decisions) != dataset_ids:
        missing = sorted(dataset_ids - set(decisions))
        extra = sorted(set(decisions) - dataset_ids)
        raise ValueError(f"queue/dataset id mismatch: missing={len(missing)} extra={len(extra)}")
    output: list[dict] = []
    for sample in dataset:
        item = dict(sample)
        decision = str(decisions[item["sample_id"]].get("decision") or "").strip().lower()
        if decision == "approve":
            item["review_status"] = "reviewed"
        elif decision == "reject":
            item["review_status"] = "rejected"
        else:
            # Blank and modify remain draft. A requested modification must be
            # made and reviewed in a later queue revision before approval.
            item["review_status"] = "draft"
        output.append(item)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.out.resolve():
        raise ValueError("refusing to overwrite the draft input dataset")
    dataset = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    output = apply_decisions(dataset, load_queue(args.queue))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in output), encoding="utf-8")
    counts: dict[str, int] = {}
    for item in output:
        status = str(item["review_status"])
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({"samples": len(output), "review_status": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
