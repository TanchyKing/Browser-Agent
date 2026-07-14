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
            ]
        ).lower()
        for slot, requirement in self.required_slots.items():
            if slot in self.completed_slots:
                continue
            checks: list[bool] = []
            if requirement.get("result_key"):
                checks.append(bool(result.get(str(requirement["result_key"]))))
            if requirement.get("evidence_contains"):
                checks.append(str(requirement["evidence_contains"]).lower() in evidence)
            if requirement.get("action"):
                checks.append(action.action == str(requirement["action"]))
            if requirement.get("target_contains"):
                checks.append(str(requirement["target_contains"]).lower() in str(action.target or "").lower())
            if "value_equals" in requirement:
                checks.append(action.value == requirement["value_equals"])
            if checks and all(checks) and bool(result.get("ok", True)):
                self.completed_slots.add(slot)

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
        }
    }
