"""Completion and duplicate-action checks over observable AgentState only."""

from __future__ import annotations

from dataclasses import dataclass

from src.agent.actions import AgentAction
from src.agent.state import AgentState, action_signature


@dataclass(frozen=True)
class VerificationDecision:
    allowed: bool
    reason: str


def verify_candidate(action: AgentAction, state: AgentState) -> VerificationDecision:
    if action_signature(action) in state.cooldown_actions:
        return VerificationDecision(False, "duplicate successful action is in cooldown")
    if action.action == "finish" and state.pending_slots:
        return VerificationDecision(
            False,
            "finish rejected; pending observable slots: " + ", ".join(sorted(state.pending_slots)),
        )
    return VerificationDecision(True, "observable completion requirements allow candidate")
