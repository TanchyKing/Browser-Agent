"""Action parsing and validation for browser-agent decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


ALLOWED_ACTIONS = {
    "observe_page",
    "click",
    "type",
    "select",
    "extract_text",
    "download_file",
    "finish",
    "request_human",
    "refuse",
}

REQUIRES_TARGET = {"click", "type", "select", "extract_text", "download_file"}
REQUIRES_VALUE = {"type", "select"}
TERMINAL_ACTIONS = {"finish", "request_human", "refuse"}
RISK_LEVELS = {"low", "medium", "high"}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentAction:
    action: str
    reason: str
    target: str | None = None
    value: str | int | float | bool | None = None
    risk_level: str = "low"
    metadata: dict[str, str | int | float | bool | None] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "AgentAction":
        action = str(raw.get("action", ""))
        target = _optional_string(raw.get("target"))
        value = _scalar_or_none(raw.get("value"))
        metadata = raw.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {"raw_metadata_error": "metadata must be an object"}
        normalized_metadata = {str(k): _scalar_or_none(v) for k, v in metadata.items()}
        if action in TERMINAL_ACTIONS and target:
            normalized_metadata.setdefault("original_target", target)
            target = None
        if action == "select" and value is None and _looks_like_select_button(target):
            normalized_metadata.setdefault("normalized_from_action", "select")
            action = "click"
        if action == "select" and _looks_like_checkbox_click(target, value):
            normalized_metadata.setdefault("normalized_from_action", "select")
            action = "click"
        return cls(
            action=action,
            target=target,
            value=value,
            reason=str(raw.get("reason", "")),
            risk_level=str(raw.get("risk_level", "low")),
            metadata=normalized_metadata,
        )

    @property
    def is_terminal(self) -> bool:
        return self.action in TERMINAL_ACTIONS

    @property
    def target_text(self) -> str:
        return " ".join(
            str(part)
            for part in [self.action, self.target, self.value]
            if part is not None and str(part).strip()
        )

    def validate(self) -> ValidationResult:
        errors: list[str] = []
        if self.action not in ALLOWED_ACTIONS:
            errors.append(f"unsupported action: {self.action}")
        if not self.reason.strip():
            errors.append("reason is required")
        if self.risk_level not in RISK_LEVELS:
            errors.append(f"unsupported risk_level: {self.risk_level}")
        if self.action in REQUIRES_TARGET and not _has_text(self.target):
            errors.append(f"{self.action} requires target")
        if self.action in REQUIRES_VALUE and self.value is None:
            errors.append(f"{self.action} requires value")
        if self.action == "observe_page" and self.target:
            errors.append("observe_page must not target a specific element")
        if self.action in TERMINAL_ACTIONS and self.target:
            errors.append(f"{self.action} must not target a browser element")
        return ValidationResult(ok=not errors, errors=tuple(errors))


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _scalar_or_none(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _has_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _looks_like_select_button(target: str | None) -> bool:
    if target is None:
        return False
    lowered = target.lower()
    if "select-" not in lowered:
        return False
    select_control_markers = [
        "filter",
        "priority",
        "plan",
        "department",
        "seniority",
        "location",
        "role",
    ]
    return not any(marker in lowered for marker in select_control_markers)


def _looks_like_checkbox_click(target: str | None, value: str | int | float | bool | None) -> bool:
    if target is None:
        return False
    lowered = target.lower()
    if any(marker in lowered for marker in ["checkbox", "approve-", "toggle-"]):
        return True
    if isinstance(value, str) and value.strip().lower() in {"on", "checked", "true", "yes"}:
        return "select" not in lowered and "filter" not in lowered
    return False
