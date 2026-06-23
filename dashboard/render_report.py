"""Render a static HTML report from an evaluation summary JSON."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return html.escape(str(value))


def render_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    analysis = payload.get("error_analysis", {})
    run_groups = payload.get("run_groups", {})
    success_checks = payload.get("success_checks", {})
    safety_outcomes = payload.get("safety_outcomes", {})
    error_counts = analysis.get("error_counts", {})
    failed_runs = analysis.get("failed_runs", [])

    metric_rows = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{_fmt(value)}</td></tr>"
        for key, value in summary.items()
        if key != "error_counts"
    )
    error_rows = "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{_fmt(value)}</td></tr>"
        for key, value in error_counts.items()
    ) or '<tr><td colspan="2">No typed errors.</td></tr>'
    failed_items = "\n".join(
        "<li>"
        + f"<strong>{html.escape(str(item.get('task_id')))}</strong> "
        + f"run={html.escape(str(item.get('run_id')))} "
        + f"status={html.escape(str(item.get('status')))} "
        + f"errors={html.escape(', '.join(event.get('type', '') for event in item.get('error_events', [])))}"
        + "</li>"
        for item in failed_runs
    ) or "<li>No failed runs in this summary.</li>"
    source_rows = _group_rows(run_groups.get("source_kind", {}))
    backend_rows = _group_rows(run_groups.get("llm_backend", {}))
    success_check_rows = _success_check_rows(success_checks)
    safety_outcome_rows = _safety_outcome_rows(safety_outcomes)
    scripted_safety_count = int((run_groups.get("source_kind", {}) or {}).get("scripted_safety", 0))
    safety_note = ""
    if scripted_safety_count:
        safety_note = (
            '<p class="warning">Scripted safety runs are policy-unit checks. '
            "They must not be described as model-driven prompt-injection resistance.</p>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Browser Agent Evaluation Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
    h1, h2 {{ color: #163b6b; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 920px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef2f7; width: 280px; }}
    code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
    .note {{ color: #6b7280; }}
    .warning {{ background: #fff7ed; border-left: 4px solid #f97316; padding: 8px 12px; }}
  </style>
</head>
<body>
  <h1>Browser Agent Evaluation Report</h1>
  <p class="note">Source: <code>{html.escape(str(payload.get('source', 'unknown')))}</code></p>
  {safety_note}

  <h2>Summary Metrics</h2>
  <table>
    {metric_rows}
  </table>

  <h2>Run Sources</h2>
  <table>
    <tr><th colspan="2">Source kind</th></tr>
    {source_rows}
    <tr><th colspan="2">LLM backend</th></tr>
    {backend_rows}
  </table>

  <h2>Error Counts</h2>
  <table>
    {error_rows}
  </table>

  <h2>Success Check Support</h2>
  <table>
    {success_check_rows}
  </table>

  <h2>Safety Outcomes</h2>
  <table>
    {safety_outcome_rows}
  </table>

  <h2>Failed Runs</h2>
  <ul>
    {failed_items}
  </ul>
</body>
</html>
"""


def _group_rows(group: dict[str, Any]) -> str:
    if not group:
        return '<tr><td colspan="2">No source metadata.</td></tr>'
    return "\n".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{_fmt(value)}</td></tr>"
        for key, value in sorted(group.items())
    )


def _success_check_rows(summary: dict[str, Any]) -> str:
    if not summary:
        return '<tr><td colspan="2">No task success-check annotations.</td></tr>'
    rows = [
        f"<tr><th>{html.escape(str(key))}</th><td>{_fmt(value)}</td></tr>"
        for key, value in summary.items()
        if key != "unsupported"
    ]
    unsupported = summary.get("unsupported") or []
    if unsupported:
        rows.append(
            "<tr><th>unsupported details</th><td>"
            + html.escape("; ".join(f"{item.get('task_id')}: {item.get('reason')}" for item in unsupported))
            + "</td></tr>"
        )
    return "\n".join(rows)


def _safety_outcome_rows(summary: dict[str, Any]) -> str:
    if not summary:
        return '<tr><td colspan="2">No safety outcome annotations.</td></tr>'
    rows = [
        f"<tr><th>{html.escape(str(key))}</th><td>{_fmt(value)}</td></tr>"
        for key, value in summary.items()
        if key not in {"failed_forbidden_action_checks", "proposed_forbidden_action_checks"}
    ]
    failed = summary.get("failed_forbidden_action_checks") or []
    if failed:
        rows.append(
            "<tr><th>failed forbidden checks</th><td>"
            + html.escape("; ".join(f"{item.get('task_id')}: {item.get('target')}" for item in failed))
            + "</td></tr>"
        )
    proposed = summary.get("proposed_forbidden_action_checks") or []
    if proposed:
        rows.append(
            "<tr><th>proposed forbidden checks</th><td>"
            + html.escape("; ".join(f"{item.get('task_id')}: {item.get('target')}" for item in proposed))
            + "</td></tr>"
        )
    return "\n".join(rows)


def render_report(summary_path: str | Path, out_html: str | Path) -> None:
    payload = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    output_path = Path(out_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render static browser-agent evaluation report.")
    parser.add_argument("--summary", required=True, help="Evaluation JSON from scripts/evaluate_tasks.py")
    parser.add_argument("--out-html", required=True, help="Output HTML report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    render_report(args.summary, args.out_html)
    print(f"Wrote {args.out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
