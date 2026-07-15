"""Strict action validation and observation-grounded schema helpers."""

from __future__ import annotations

import ast
import copy
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ActionName = Literal[
    "observe_page",
    "click",
    "type",
    "select",
    "extract_text",
    "download_file",
    "finish",
    "request_human",
    "refuse",
]
Scalar = str | int | float | bool | None


class StructuredAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    action: ActionName
    reason: str = Field(min_length=1, max_length=160)
    target: str | None = Field(default=None, max_length=512)
    value: Scalar = None
    risk_level: Literal["low", "medium", "high"] = "low"
    metadata: dict[str, Scalar] = Field(default_factory=dict, max_length=8)

    @field_validator("metadata")
    @classmethod
    def validate_metadata_keys(cls, value: dict[str, Scalar]) -> dict[str, Scalar]:
        if any(len(key) > 64 for key in value):
            raise ValueError("metadata keys must be <= 64 characters")
        if any(isinstance(item, str) and len(item) > 512 for item in value.values()):
            raise ValueError("metadata string values must be <= 512 characters")
        return value

    @model_validator(mode="after")
    def validate_action_contract(self) -> "StructuredAction":
        if self.action in {"click", "type", "select", "extract_text", "download_file"} and not self.target:
            raise ValueError(f"{self.action} requires target")
        if self.action in {"type", "select"} and self.value is None:
            raise ValueError(f"{self.action} requires value")
        if self.action in {"finish", "request_human", "refuse", "observe_page"} and self.target is not None:
            raise ValueError(f"{self.action} requires target=null")
        return self


class StructuredActionWithTerminalAnswer(StructuredAction):
    answer: str | None = Field(default=None, min_length=1, max_length=320)

    @model_validator(mode="after")
    def validate_terminal_answer_contract(self) -> "StructuredActionWithTerminalAnswer":
        is_terminal = self.action in {"finish", "request_human", "refuse"}
        if is_terminal and not self.answer:
            raise ValueError(f"{self.action} requires answer")
        if not is_terminal and self.answer is not None:
            raise ValueError("answer is only allowed for terminal actions")
        return self


def validate_structured_action(
    payload: Mapping[str, Any],
    *,
    terminal_answer_enabled: bool = False,
) -> dict[str, Any]:
    model = StructuredActionWithTerminalAnswer if terminal_answer_enabled else StructuredAction
    return model.model_validate(dict(payload)).model_dump()


def observation_grounded_schema(
    base_schema: Mapping[str, Any],
    observation: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a schema constrained to selectors/options visible this turn."""

    selectors, select_options = observation_candidates(observation)
    schema = copy.deepcopy(dict(base_schema))
    properties = schema.setdefault("properties", {})
    if selectors:
        properties.setdefault("target", {})["enum"] = [*selectors, None]
    if select_options:
        schema.setdefault("allOf", []).append(
            {
                "if": {
                    "properties": {"action": {"const": "select"}},
                    "required": ["action"],
                },
                "then": {
                    "properties": {"value": {"enum": select_options}},
                },
            }
        )
    return schema, {"selectors": selectors, "select_options": select_options}


def observation_candidates(observation: str) -> tuple[list[str], list[Scalar]]:
    selectors: list[str] = []
    options: list[Scalar] = []
    for line in observation.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- selector: ") or "; tag:" not in stripped:
            continue
        selector = stripped[len("- selector: ") :].split("; tag:", 1)[0].strip()
        if selector and selector not in selectors:
            selectors.append(selector)
        if "; options: " not in stripped:
            continue
        raw_options = stripped.split("; options: ", 1)[1].strip()
        try:
            parsed = ast.literal_eval(raw_options)
        except (SyntaxError, ValueError):
            continue
        for item in parsed if isinstance(parsed, list) else []:
            value = item.get("value") if isinstance(item, dict) else item
            if value is not None and isinstance(value, (str, int, float, bool)) and value not in options:
                options.append(value)
    return selectors, options
