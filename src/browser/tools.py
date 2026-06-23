"""Typed browser tool inputs and outputs.

These classes are intentionally small and framework-neutral so the agent layer
can validate actions without depending on Playwright internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ActionName = Literal[
    "observe_page",
    "click",
    "type",
    "select",
    "extract_text",
    "download_file",
    "finish",
]


class BrowserToolError(RuntimeError):
    """Base error for browser tool failures."""


class MissingBrowserDependency(BrowserToolError):
    """Raised when an optional browser runtime dependency is unavailable."""


@dataclass(frozen=True)
class BrowserAction:
    """A single normalized browser action."""

    name: ActionName
    selector: str | None = None
    text: str | None = None
    value: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate the action shape before any browser side effects."""

        if self.name in {"click", "type", "select", "extract_text"} and not self.selector:
            raise BrowserToolError(f"{self.name} requires a selector")
        if self.name == "type" and self.text is None:
            raise BrowserToolError("type requires text")
        if self.name == "select" and self.value is None:
            raise BrowserToolError("select requires value")
        if self.name == "finish" and not self.reason:
            raise BrowserToolError("finish requires a reason")


@dataclass(frozen=True)
class BrowserObservation:
    """A compact page observation suitable for traces and LLM prompts."""

    url: str
    title: str
    text: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    screenshot_path: str | None = None


@dataclass(frozen=True)
class BrowserActionResult:
    """Result of executing a browser action."""

    action: BrowserAction
    ok: bool
    observation: BrowserObservation | None = None
    extracted_text: str | None = None
    download_path: str | None = None
    error_type: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def failure(
        cls,
        action: BrowserAction,
        error: str,
        *,
        error_type: str = "browser_error",
    ) -> "BrowserActionResult":
        return cls(action=action, ok=False, error=error, error_type=error_type)
