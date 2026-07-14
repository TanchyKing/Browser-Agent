"""Short deterministic pre-action critic; the hard policy remains authoritative."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.agent.actions import AgentAction
from src.agent.state import action_to_mapping


@dataclass(frozen=True)
class CriticDecision:
    allowed: bool
    reason: str
    replacement: AgentAction | None = None

    def audit(self, original: AgentAction) -> dict[str, Any]:
        return {
            "original_candidate": action_to_mapping(original),
            "critic_decision": {"allowed": self.allowed, "reason": self.reason},
            "replacement_candidate": (
                action_to_mapping(self.replacement) if self.replacement is not None else None
            ),
        }


def review_action(
    action: AgentAction,
    *,
    forbidden_actions: list[dict[str, Any]],
) -> CriticDecision:
    target = _normalize(action.target or "")
    forbidden_targets = {
        _normalize(str(item.get("selector") or ""))
        for item in forbidden_actions
        if item.get("selector")
    }
    high_impact = action.action in {"click", "type", "select", "download_file"} and (
        target in forbidden_targets
        or action.risk_level == "high"
        or str(action.metadata.get("source") or "").lower() == "page_instruction"
    )
    if not high_impact:
        return CriticDecision(True, "candidate is grounded and has no critic-level risk marker")
    replacement = AgentAction(
        action="request_human",
        reason="Need confirmation for a high-impact page-requested action.",
        risk_level="high",
        metadata={
            "requested_input": "Confirm whether this high-impact action is authorized.",
            "critic_replacement": True,
        },
    )
    return CriticDecision(False, "candidate has forbidden or untrusted high-impact provenance", replacement)


def _normalize(value: str) -> str:
    return value.strip().replace('"', "'")
