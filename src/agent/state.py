"""Deterministic, agent-visible execution state for multi-step tasks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from src.agent.actions import AgentAction
from src.task_contract import TaskContract


@dataclass
class AgentState:
    task_goal: str
    required_slots: dict[str, dict[str, Any]] = field(default_factory=dict)
    completed_slots: set[str] = field(default_factory=set)
    slot_values: dict[str, Any] = field(default_factory=dict)
    current_page: str = ""
    last_action: dict[str, Any] | None = None
    last_result: dict[str, Any] | None = None
    blocked_actions: list[dict[str, Any]] = field(default_factory=list)
    cooldown_actions: set[tuple[str, str | None, Any]] = field(default_factory=set)
    step_budget: int = 8

    @classmethod
    def from_contract(cls, contract: TaskContract, *, step_budget: int) -> "AgentState":
        return cls(
            task_goal=contract.instruction,
            required_slots={key: dict(value) for key, value in contract.required_slots.items()},
            step_budget=step_budget,
        )

    @property
    def pending_slots(self) -> set[str]:
        return set(self.required_slots) - self.completed_slots

    def record_result(
        self,
        action: AgentAction,
        result: dict[str, Any],
        *,
        observation: str,
    ) -> None:
        self.current_page = observation.splitlines()[0] if observation else ""
        self.last_action = action_to_mapping(action)
        self.last_result = _public_result(result)
        evidence = "\n".join(
            [
                observation,
                str(result.get("extracted_text") or ""),
                str(result.get("download_path") or ""),
                json.dumps(result.get("metadata") or {}, ensure_ascii=False, sort_keys=True),
                json.dumps(result.get("post_observation") or {}, ensure_ascii=False, sort_keys=True),
            ]
        ).lower()
        for slot, requirement in self.required_slots.items():
            checks: list[bool] = []
            if requirement.get("result_key"):
                checks.append(bool(result.get(str(requirement["result_key"]))))
            if requirement.get("result_not_equals") is not None and requirement.get("result_key"):
                result_value = result.get(str(requirement["result_key"]))
                checks.append(str(result_value).strip() != str(requirement["result_not_equals"]))
            if requirement.get("evidence_contains"):
                checks.append(str(requirement["evidence_contains"]).lower() in evidence)
            if requirement.get("action"):
                checks.append(action.action == str(requirement["action"]))
            if requirement.get("target_contains"):
                checks.append(str(requirement["target_contains"]).lower() in str(action.target or "").lower())
            if "value_equals" in requirement:
                checks.append(action.value == requirement["value_equals"])
            if requirement.get("value_from_slot"):
                source_slot = str(requirement["value_from_slot"])
                checks.append(source_slot in self.slot_values and action.value == self.slot_values[source_slot])
            postcondition = _observable_postcondition(action, requirement, result.get("post_observation"))
            if checks and all(checks) and postcondition and bool(result.get("ok", True)):
                self.completed_slots.add(slot)
                if requirement.get("capture_result"):
                    captured = result.get(str(requirement["capture_result"]))
                    if captured is not None:
                        self.slot_values[slot] = captured.strip() if isinstance(captured, str) else captured
            elif slot in self.completed_slots and _same_target(action, requirement) and not postcondition:
                self.completed_slots.remove(slot)

    def observe(self, observation: str) -> None:
        self.current_page = observation.splitlines()[0] if observation else ""
        lowered = observation.lower()
        for slot, requirement in self.required_slots.items():
            contains = requirement.get("evidence_contains")
            if slot not in self.completed_slots and contains and str(contains).lower() in lowered:
                self.completed_slots.add(slot)

    def add_blocked(self, action: AgentAction, reason: str) -> None:
        self.blocked_actions.append({**action_to_mapping(action), "block_reason": reason})

    def snapshot(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["completed_slots"] = sorted(self.completed_slots)
        payload["pending_slots"] = sorted(self.pending_slots)
        payload["cooldown_actions"] = [list(item) for item in sorted(self.cooldown_actions, key=str)]
        return payload


def action_signature(action: AgentAction) -> tuple[str, str | None, Any]:
    return (action.action, action.target, action.value)


def action_to_mapping(action: AgentAction) -> dict[str, Any]:
    return {
        "action": action.action,
        "target": action.target,
        "value": action.value,
        "reason": action.reason,
        "risk_level": action.risk_level,
        "metadata": dict(action.metadata),
    }


def _public_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if key
        not in {
            "llm_attempts",
            "json_first_error",
            "post_observation",
        }
    }


def _observable_postcondition(
    action: AgentAction,
    requirement: dict[str, Any],
    post_observation: Any,
) -> bool:
    if action.action not in {"type", "select", "click"}:
        return True
    if not isinstance(post_observation, dict):
        return False

    target_element = _find_element(post_observation, action.target)
    if action.action in {"type", "select"}:
        if target_element is None:
            return False
        observed_value = target_element.get("value")
        return str(observed_value) == str(action.value)

    if target_element and str(target_element.get("type") or "").lower() in {"checkbox", "radio"}:
        return bool(target_element.get("checked")) == bool(requirement.get("checked_equals", True))

    evidence_target = requirement.get("evidence_target")
    if not evidence_target:
        return False
    evidence_element = _find_element(post_observation, str(evidence_target))
    observed = (
        str(evidence_element.get("value") or evidence_element.get("text") or "").strip()
        if evidence_element is not None
        else ""
    )
    body_text = str(post_observation.get("text") or "")
    body_lines = {line.strip() for line in body_text.splitlines() if line.strip()}
    if "evidence_equals" in requirement:
        expected = str(requirement["evidence_equals"])
        return observed == expected if evidence_element is not None else expected in body_lines
    if "evidence_not_equals" in requirement:
        initial = str(requirement["evidence_not_equals"])
        return observed != initial if evidence_element is not None else initial not in body_lines
    if requirement.get("evidence_contains"):
        needle = str(requirement["evidence_contains"]).lower()
        return needle in (observed if evidence_element is not None else body_text).lower()
    return bool(observed)


def _same_target(action: AgentAction, requirement: dict[str, Any]) -> bool:
    contains = requirement.get("target_contains")
    return bool(contains and str(contains).lower() in str(action.target or "").lower())


def _find_element(observation: dict[str, Any], selector: str | None) -> dict[str, Any] | None:
    wanted = _selector_key(selector)
    if not wanted:
        return None
    for element in observation.get("elements") or []:
        if isinstance(element, dict) and wanted in _element_selector_keys(element):
            return element
    return None


def _element_selector_keys(element: dict[str, Any]) -> set[str]:
    keys = {_selector_key(element.get("selector"))}
    if element.get("id"):
        keys.add(_selector_key(f"#{element['id']}"))
    if element.get("testid"):
        keys.add(_selector_key(f"[data-testid='{element['testid']}']"))
    if element.get("name"):
        tag = str(element.get("tag") or "*")
        keys.add(_selector_key(f"{tag}[name='{element['name']}']"))
    return {key for key in keys if key}


def _selector_key(selector: Any) -> str:
    text = str(selector or "").strip().lower().replace('"', "'")
    return "".join(text.split())
