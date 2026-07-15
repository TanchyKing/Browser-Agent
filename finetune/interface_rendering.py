"""Render one reviewed semantic action into the R10e or R10f interface."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from src.llm.structured_output import observation_grounded_schema, validate_structured_action


ROOT = Path(__file__).resolve().parents[1]
INTERFACES = {"r10e", "r10f"}
TERMINAL_ACTIONS = {"finish", "request_human", "refuse"}
TERMINAL_ACTION_REASONS = {
    "finish": "Return the observed result.",
    "request_human": "Request the required confirmation.",
    "refuse": "Refuse the unsafe request.",
}


def semantic_completion(
    completion: Mapping[str, Any],
) -> dict[str, str | None]:
    """Create the interface-neutral fields that a human reviews once."""

    action = str(completion.get("action") or "")
    reason = str(completion.get("reason") or "").strip()
    if action in TERMINAL_ACTIONS:
        return {
            "action_reason": TERMINAL_ACTION_REASONS[action],
            "user_visible_result": reason,
        }
    return {"action_reason": reason, "user_visible_result": None}


def render_completion(
    completion: Mapping[str, Any],
    semantics: Mapping[str, Any],
    interface: str,
) -> dict[str, Any]:
    """Render completion fields without changing their reviewed semantics."""

    if interface not in INTERFACES:
        raise ValueError(f"unsupported interface: {interface}")
    rendered = copy.deepcopy(dict(completion))
    action = str(rendered.get("action") or "")
    action_reason = str(semantics.get("action_reason") or "").strip()
    user_visible_result = semantics.get("user_visible_result")
    if not action_reason:
        raise ValueError("semantic_completion.action_reason is required")
    if action in TERMINAL_ACTIONS:
        if not isinstance(user_visible_result, str) or not user_visible_result.strip():
            raise ValueError("terminal semantic_completion.user_visible_result is required")
        if interface == "r10e":
            rendered["reason"] = user_visible_result.strip()
            rendered.pop("answer", None)
        else:
            rendered["reason"] = action_reason
            rendered["answer"] = user_visible_result.strip()
    else:
        if user_visible_result is not None:
            raise ValueError("non-terminal semantic_completion.user_visible_result must be null")
        rendered["reason"] = action_reason
        rendered.pop("answer", None)
    validate_structured_action(rendered, terminal_answer_enabled=interface == "r10f")
    return rendered


def render_tools_schema(sample: Mapping[str, Any], interface: str) -> dict[str, Any]:
    if interface not in INTERFACES:
        raise ValueError(f"unsupported interface: {interface}")
    if interface == "r10e":
        return copy.deepcopy(dict(sample.get("tools_schema") or {}))
    base = json.loads(
        (ROOT / "configs" / "schema" / "action.terminal-answer.schema.json").read_text(
            encoding="utf-8"
        )
    )
    schema, _ = observation_grounded_schema(base, str(sample.get("observation") or ""))
    return schema


def render_sample(sample: Mapping[str, Any], interface: str) -> dict[str, Any]:
    rendered = copy.deepcopy(dict(sample))
    rendered["completion"] = render_completion(
        rendered.get("completion") or {},
        rendered.get("semantic_completion") or {},
        interface,
    )
    rendered["tools_schema"] = render_tools_schema(rendered, interface)
    errors = list(Draft202012Validator(rendered["tools_schema"]).iter_errors(rendered["completion"]))
    if errors:
        messages = "; ".join(error.message for error in errors[:3])
        raise ValueError(f"rendered {interface} completion violates tools schema: {messages}")
    return rendered
