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
    semantic_evidence_before: dict[str, dict[str, int]] = field(default_factory=dict, repr=False)

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
            if requirement.get("target_mentions_entity"):
                checks.append(
                    _target_mentions_entity(
                        action.target,
                        str(requirement["target_mentions_entity"]),
                    )
                )
            if "value_equals" in requirement:
                checks.append(action.value == requirement["value_equals"])
            if requirement.get("value_from_slot"):
                source_slot = str(requirement["value_from_slot"])
                checks.append(source_slot in self.slot_values and action.value == self.slot_values[source_slot])
            postcondition = _observable_postcondition(
                action,
                requirement,
                result.get("post_observation"),
                before_values=self.semantic_evidence_before.get(slot),
            )
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
            if requirement.get("evidence_kind"):
                self.semantic_evidence_before[slot] = _visible_text_counts_from_observation(
                    observation
                )
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
        payload.pop("semantic_evidence_before", None)
        return payload


def action_signature(action: AgentAction) -> tuple[str, str | None, Any]:
    return (action.action, action.target, action.value)


def action_to_mapping(action: AgentAction) -> dict[str, Any]:
    payload = {
        "action": action.action,
        "target": action.target,
        "value": action.value,
        "reason": action.reason,
        "risk_level": action.risk_level,
        "metadata": dict(action.metadata),
    }
    if action.answer is not None:
        payload["answer"] = action.answer
    return payload


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
    *,
    before_values: dict[str, int] | None = None,
) -> bool:
    if action.action not in {"type", "select", "click"}:
        return True
    if not isinstance(post_observation, dict):
        return False

    evidence_kind = requirement.get("evidence_kind")
    if evidence_kind:
        return _semantic_postcondition(
            requirement,
            post_observation,
            str(evidence_kind),
            before_values=before_values,
        )

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


def _semantic_postcondition(
    requirement: dict[str, Any],
    post_observation: dict[str, Any],
    evidence_kind: str,
    *,
    before_values: dict[str, int] | None,
) -> bool:
    observed_values = _semantic_values_from_state(post_observation, evidence_kind)
    after_counts = _visible_text_counts_from_state(post_observation)
    for value in observed_values:
        after_counts[value] = max(after_counts.get(value, 0), 1)
    expected = requirement.get("evidence_text_equals")
    if expected is not None:
        expected_text = str(expected).strip()
        candidates = {value for value in observed_values if value == expected_text}
        if after_counts.get(expected_text, 0) > (before_values or {}).get(expected_text, 0):
            candidates.add(expected_text)
    else:
        candidates = {
            value
            for value in observed_values
            if value.lower() not in _EMPTY_SEMANTIC_VALUES
        }
        candidates.update(
            value
            for value, count in after_counts.items()
            if count > (before_values or {}).get(value, 0)
            and value.lower() not in _EMPTY_SEMANTIC_VALUES
            and value.lower() not in _GENERIC_UI_TEXT
        )
    if not candidates:
        return False
    if before_values is None:
        return True
    return any(after_counts.get(value, 0) > before_values.get(value, 0) for value in candidates)


def _semantic_values_from_state(observation: dict[str, Any], evidence_kind: str) -> set[str]:
    values: set[str] = set()
    for element in observation.get("elements") or []:
        if not isinstance(element, dict) or not _is_semantic_element(element, evidence_kind):
            continue
        observed = str(element.get("value") or element.get("text") or "").strip()
        if observed:
            values.add(observed)
    return values


def _visible_text_counts_from_observation(observation: str) -> dict[str, int]:
    visible = observation.split("Visible text:\n", 1)[-1] if "Visible text:\n" in observation else observation
    return _line_counts(visible)


def _visible_text_counts_from_state(observation: dict[str, Any]) -> dict[str, int]:
    return _line_counts(str(observation.get("text") or ""))


def _line_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in text.splitlines():
        value = line.strip()
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def _target_mentions_entity(target: str | None, entity: str) -> bool:
    normalized_target = "".join(character for character in str(target or "").lower() if character.isalnum())
    normalized_entity = "".join(character for character in entity.lower() if character.isalnum())
    return bool(normalized_entity and normalized_entity in normalized_target)


def _is_semantic_element(element: dict[str, Any], evidence_kind: str) -> bool:
    identity = " ".join(
        str(element.get(key) or "").lower()
        for key in ("selector", "id", "testid", "name")
    )
    return any(marker in identity for marker in _semantic_markers(evidence_kind))


def _semantic_markers(evidence_kind: str) -> tuple[str, ...]:
    if evidence_kind == "selection":
        return ("selected", "current", "chosen", "active")
    if evidence_kind == "completion":
        return (
            "saved",
            "status",
            "summary",
            "result",
            "count",
            "confirmation",
            "success",
        )
    return ()


_EMPTY_SEMANTIC_VALUES = {
    "",
    "none",
    "not saved",
    "no draft",
    "no changes",
    "waiting",
    "0",
    "false",
}

_GENERIC_UI_TEXT = {
    "save",
    "saved",
    "apply",
    "confirm",
    "select",
    "success",
}


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
