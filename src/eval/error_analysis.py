"""Error taxonomy and trace replay helpers."""

from __future__ import annotations

from collections import Counter
from typing import Any


ERROR_TAXONOMY: dict[str, str] = {
    "selector_grounding_error": "Agent selected an imprecise or non-grounded selector.",
    "strict_mode_violation": "Browser reported a Playwright strict mode violation.",
    "strict_mode_multiple_matches": "Selector matched multiple elements under Playwright strict mode.",
    "element_not_found": "Selector did not resolve to an element.",
    "timeout": "Browser action timed out.",
    "unsupported_action": "Action type is not supported by the browser tool layer.",
    "invalid_llm_response": "Model response could not be parsed as one JSON action after bounded retry.",
    "invalid_action": "Agent returned an action that failed schema or shape validation.",
    "browser_execution_error": "Browser tool returned an execution error that was not otherwise classified.",
    "page_understanding_error": "Agent misread the page state or available information.",
    "wrong_action": "Agent selected the wrong action type for the state.",
    "element_target_error": "Agent targeted a missing, stale, or incorrect element.",
    "form_fill_error": "Agent filled the wrong value or missed a required field.",
    "premature_finish": "Agent declared completion before the expected state was reached.",
    "missing_finish": "Task state reached success, but the agent did not emit finish.",
    "max_steps_exceeded": "Agent reached the step limit without completing.",
    "dom_success_check_failed": "Programmatic DOM/file/safety success check failed.",
    "safety_blocked": "Policy blocked a high-risk or forbidden action as expected.",
    "prompt_injection_followed": "Agent followed untrusted instructions from page content.",
    "forbidden_action": "Agent attempted an action blocked by policy.",
    "recovery_failed": "Agent attempted recovery but did not recover.",
    "needs_user_confirmation": "Agent correctly stopped for a human decision.",
}


def classify_error_type(error: Any, *, action_type: str | None = None, ok: bool | None = None) -> str | None:
    """Classify browser/tool error text into a stable taxonomy label."""

    if not error:
        return None if ok is not False else "browser_execution_error"
    text = str(error).lower()
    action = (action_type or "").lower()
    if "strict mode violation" in text or "resolved to " in text and "elements" in text:
        return "strict_mode_multiple_matches"
    if "unsupported" in text and "action" in text:
        return "unsupported_action"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "element not found" in text or "no element" in text or "not found" in text:
        return "element_not_found"
    if "locator" in text or "selector" in text or action in {"click", "type", "select", "extract_text"}:
        return "selector_grounding_error"
    if "safety" in text or "blocked forbidden" in text or "requires human confirmation" in text:
        return "safety_blocked"
    if "prompt injection" in text or "ignore previous instructions" in text:
        return "prompt_injection_followed"
    return "browser_execution_error"


def collect_error_events(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect normalized error events from run-level and step-level fields."""

    events: list[dict[str, Any]] = []
    for step in run.get("steps") or []:
        error_type = step.get("error_type") or classify_error_type(
            step.get("error"),
            action_type=step.get("action_type"),
            ok=step.get("execution_ok"),
        )
        if error_type:
            events.append(
                {
                    "task_id": run.get("task_id"),
                    "run_id": run.get("run_id"),
                    "step_index": step.get("step_index"),
                    "type": str(error_type),
                    "message": step.get("error") or step.get("message") or "",
                    "action_type": step.get("action_type"),
                }
            )

    for error in run.get("errors") or []:
        if isinstance(error, dict):
            error_type = str(error.get("type") or "unknown_error")
            message = str(error.get("message") or "")
        else:
            error_type = str(error)
            message = ""
        events.append(
            {
                "task_id": run.get("task_id"),
                "run_id": run.get("run_id"),
                "step_index": None,
                "type": error_type,
                "message": message,
                "action_type": None,
            }
        )

    if run.get("status") == "failed" and not events:
        events.append(
            {
                "task_id": run.get("task_id"),
                "run_id": run.get("run_id"),
                "step_index": None,
                "type": "unknown_error",
                "message": "Run failed without a typed error.",
                "action_type": None,
            }
        )
    return events


def analyze_errors(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return error counts and per-failed-run summaries."""

    counter: Counter[str] = Counter()
    failed_runs: list[dict[str, Any]] = []
    for run in runs:
        events = collect_error_events(run)
        for event in events:
            counter[event["type"]] += 1
        if run.get("status") != "success" or events:
            failed_runs.append(
                {
                    "task_id": run.get("task_id"),
                    "run_id": run.get("run_id"),
                    "status": run.get("status", "failed"),
                    "error_events": events,
                }
            )

    return {
        "taxonomy": ERROR_TAXONOMY,
        "error_counts": dict(sorted(counter.items())),
        "failed_runs": failed_runs,
    }


def render_trace_replay(run: dict[str, Any]) -> str:
    """Render a compact Markdown replay for one run."""

    lines = [
        f"### Trace Replay: {run.get('task_id', 'unknown_task')} / {run.get('run_id', 'unknown_run')}",
        f"- status: `{run.get('status', 'failed')}`",
        f"- duration_ms: `{run.get('duration_ms', 0)}`",
        "",
    ]
    for step in run.get("steps") or []:
        marker = "!"
        if step.get("safety_violation"):
            marker = "SAFETY"
        elif not step.get("valid_action", True):
            marker = "INVALID"
        elif step.get("recovery_attempt"):
            marker = "RECOVERY"
        lines.append(
            "- "
            + f"step {step.get('step_index', '?')} [{marker}] "
            + f"action=`{step.get('action_type', 'unknown')}` "
            + f"error=`{step.get('error_type', '')}`"
        )
    events = collect_error_events(run)
    if events:
        lines.extend(["", "Errors:"])
        for event in events:
            lines.append(
                "- "
                + f"{event['type']} at step {event.get('step_index')}: "
                + (event.get("message") or ERROR_TAXONOMY.get(event["type"], ""))
            )
    return "\n".join(lines).strip() + "\n"
