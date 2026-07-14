"""Agent-visible task contract that excludes evaluator-private success oracles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TaskContract:
    instruction: str
    allowed_actions: tuple[str, ...] = ()
    public_constraints: tuple[str, ...] = ()

    @classmethod
    def from_task(cls, task: Mapping[str, Any]) -> "TaskContract":
        public = task.get("agent_contract") or {}
        constraints = public.get("constraints") if isinstance(public, dict) else None
        return cls(
            instruction=str(task.get("instruction") or "").strip(),
            allowed_actions=tuple(str(item) for item in task.get("allowed_actions") or []),
            public_constraints=tuple(str(item) for item in constraints or []),
        )

    def to_prompt(self) -> str:
        lines = ["User task:", self.instruction]
        if self.allowed_actions:
            lines.extend(["", "Allowed action types:", ", ".join(self.allowed_actions)])
        if self.public_constraints:
            lines.extend(["", "User-visible constraints:"])
            lines.extend(f"- {constraint}" for constraint in self.public_constraints)
        lines.extend(
            [
                "",
                "Completion contract:",
                "Use only evidence available in page observations and tool results.",
                "Return finish only after that observable evidence proves the user task is complete.",
            ]
        )
        return "\n".join(lines)
