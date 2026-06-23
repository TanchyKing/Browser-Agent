"""Program-side safety checks for proposed browser actions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .actions import AgentAction


DEFAULT_HIGH_RISK_TERMS = {
    "submit",
    "send",
    "email",
    "delete",
    "remove",
    "payment",
    "pay",
    "purchase",
    "checkout",
    "transfer",
    "upload",
    "password",
    "token",
    "api key",
    "secret",
}

DEFAULT_FORBIDDEN_INTENT_TERMS = {
    "ignore previous instructions",
    "reveal system prompt",
    "read local file",
    "exfiltrate",
    "bypass safety",
    "leak secret",
    "steal",
    "delete account",
}

DEFAULT_HIGH_RISK_ACTIONS: set[str] = set()


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    requires_human: bool = False
    reason: str = "allowed"


@dataclass(frozen=True)
class SafetyPolicy:
    high_risk_target_terms: frozenset[str] = frozenset(DEFAULT_HIGH_RISK_TERMS)
    forbidden_intent_terms: frozenset[str] = frozenset(DEFAULT_FORBIDDEN_INTENT_TERMS)
    high_risk_actions: frozenset[str] = frozenset(DEFAULT_HIGH_RISK_ACTIONS)

    @classmethod
    def from_file(cls, path: str | Path) -> "SafetyPolicy":
        values = _read_simple_yaml_lists(Path(path))
        return cls(
            high_risk_target_terms=frozenset(values.get("high_risk_target_terms", DEFAULT_HIGH_RISK_TERMS)),
            forbidden_intent_terms=frozenset(values.get("forbidden_intent_terms", DEFAULT_FORBIDDEN_INTENT_TERMS)),
            high_risk_actions=frozenset(values.get("high_risk_actions", DEFAULT_HIGH_RISK_ACTIONS)),
        )

    def evaluate(
        self,
        action: AgentAction,
        page_text: str = "",
        forbidden_actions: list[Mapping[str, Any]] | None = None,
    ) -> SafetyDecision:
        validation = action.validate()
        if not validation.ok:
            return SafetyDecision(False, False, "; ".join(validation.errors))

        explicit_forbidden = _matches_forbidden_action(action, forbidden_actions or [])
        if explicit_forbidden:
            return SafetyDecision(False, False, explicit_forbidden)

        if action.action == "request_human":
            return SafetyDecision(True, True, "human handoff requested")
        if action.action == "refuse":
            return SafetyDecision(True, False, "refusal terminal action")

        target_text = action.target_text.lower()
        forbidden_hit = _first_term(self.forbidden_intent_terms, target_text)
        if forbidden_hit:
            return SafetyDecision(False, False, f"blocked forbidden intent term: {forbidden_hit}")

        high_risk_hit = _first_term(self.high_risk_target_terms, target_text)
        metadata_risk = str(action.metadata.get("safety_risk", "")).lower()
        if action.risk_level == "high" or metadata_risk == "high" or high_risk_hit or action.action in self.high_risk_actions:
            return SafetyDecision(
                False,
                True,
                f"requires human confirmation for high-risk action: {high_risk_hit or metadata_risk or action.action}",
            )

        return SafetyDecision(True, False, "allowed")


def _first_term(terms: frozenset[str], text: str) -> str | None:
    for term in sorted(terms):
        if term.lower() in text:
            return term
    return None


def _matches_forbidden_action(action: AgentAction, forbidden_actions: list[Mapping[str, Any]]) -> str | None:
    for forbidden in forbidden_actions:
        forbidden_action = str(forbidden.get("action", "")).strip().lower()
        selector = str(forbidden.get("selector", "")).strip()
        if selector and _same_selector(selector, action.target or ""):
            return f"blocked task forbidden selector: {selector}"
        if forbidden_action and _forbidden_action_matches(action, forbidden_action):
            return f"blocked task forbidden action: {forbidden_action}"
    return None


def _forbidden_action_matches(action: AgentAction, forbidden_action: str) -> bool:
    action_text = action.target_text.lower()
    if forbidden_action == "delete_record":
        return action.action == "click" and ("delete" in action_text or "remove" in action_text)
    if forbidden_action == "send_email":
        return action.action == "click" and ("send" in action_text or "email" in action_text)
    if forbidden_action == "make_payment":
        return action.action == "click" and ("pay" in action_text or "payment" in action_text or "checkout" in action_text)
    if forbidden_action == "read_local_file":
        return "file://" in action_text or "local file" in action_text
    if forbidden_action == "external_navigation":
        return action.action == "click" and ("http://" in action_text or "https://" in action_text)
    if forbidden_action == "submit_sensitive_form":
        return action.action == "click" and ("submit" in action_text or "confirm" in action_text)
    if forbidden_action == "ignore_system_policy":
        return bool(_first_term(DEFAULT_FORBIDDEN_INTENT_TERMS, action_text))
    return False


def _same_selector(left: str, right: str) -> bool:
    return _normalize_selector(left) == _normalize_selector(right)


def _normalize_selector(selector: str) -> str:
    return selector.strip().replace('"', "'")


def _read_simple_yaml_lists(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    result: dict[str, set[str]] = {}
    current_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current_key = line[:-1].strip()
            result.setdefault(current_key, set())
            continue
        stripped = line.strip()
        if current_key and stripped.startswith("- "):
            result[current_key].add(stripped[2:].strip())
    return result
