"""Dependency-light LLM adapter skeletons.

The project starts with deterministic mock adapters so the agent loop and safety
checks can be tested without API keys, network, or a running local model.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    task: str
    observation: str
    action_schema: dict | None = None
    candidate_snapshot: dict | None = None
    safety_policy: str | None = None
    step_index: int = 0


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str = "mock"
    raw: dict | None = None

    def as_json(self) -> dict:
        parsed = json.loads(self.content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON must be an object")
        return parsed


class BaseLLMAdapter(Protocol):
    model_name: str

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return one proposed action as JSON text."""


class MockLLMAdapter:
    """Queue-backed deterministic adapter for tests and offline smoke runs."""

    model_name = "mock"

    def __init__(self, responses: list[dict | str] | None = None) -> None:
        self._responses = list(responses or [])

    def complete(self, request: LLMRequest) -> LLMResponse:
        if self._responses:
            payload = self._responses.pop(0)
        else:
            payload = {
                "action": "finish",
                "reason": "mock adapter default finish",
                "risk_level": "low",
            }
        if isinstance(payload, str):
            content = payload
        else:
            content = json.dumps(payload, ensure_ascii=False)
        return LLMResponse(content=content, model=self.model_name, raw={"step_index": request.step_index})


class StaticJSONAdapter(MockLLMAdapter):
    """Alias for tests that need to make the deterministic behavior explicit."""


class ObservationDrivenMockLLMAdapter:
    """Small heuristic mock for model-driven safety and recovery tests."""

    model_name = "observation-driven-mock"

    def __init__(self) -> None:
        self._issued_recovery_action = False

    def complete(self, request: LLMRequest) -> LLMResponse:
        observation = request.observation.lower()
        if self._issued_recovery_action:
            payload = {
                "action": "finish",
                "reason": "recovery action completed",
                "risk_level": "low",
            }
            self._issued_recovery_action = False
        elif "previous action failed" in observation and "northstar clinics" in observation:
            payload = {
                "action": "click",
                "target": "tr[data-name='Northstar Clinics'] button",
                "reason": "retry with specific row selector",
                "risk_level": "low",
                "metadata": {"recovery": True},
            }
            self._issued_recovery_action = True
        elif "northstar clinics" in observation and "select" in observation:
            payload = {
                "action": "click",
                "target": "button:has-text('Select')",
                "reason": "select matching row",
                "risk_level": "low",
            }
        elif "danger-delete" in observation or "delete all records" in observation:
            payload = {
                "action": "click",
                "target": "#danger-delete",
                "reason": "page asks for deletion",
                "risk_level": "low",
                "metadata": {"source": "page_instruction"},
            }
        else:
            payload = {
                "action": "finish",
                "reason": "mock completed",
                "risk_level": "low",
            }
        return LLMResponse(
            content=json.dumps(payload, ensure_ascii=False),
            model=self.model_name,
            raw={"step_index": request.step_index},
        )


class OllamaAdapter:
    """Minimal Ollama adapter using stdlib HTTP.

    This class is intentionally not exercised in skeleton tests. It exists so
    integration work can be added later without changing the agent loop API.
    """

    def __init__(
        self,
        model_name: str = "qwen3:8b",
        endpoint: str = "http://localhost:11434/api/generate",
        timeout_seconds: int = 180,
        *,
        think: bool | None = None,
        format_mode: str = "json",
        temperature: float = 0.0,
        num_predict: int = 768,
    ) -> None:
        if format_mode not in {"json", "schema"}:
            raise ValueError("format_mode must be 'json' or 'schema'")
        if num_predict < 1:
            raise ValueError("num_predict must be >= 1")
        self.model_name = model_name
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.think = think
        self.format_mode = format_mode
        self.temperature = temperature
        self.num_predict = num_predict

    def complete(self, request: LLMRequest) -> LLMResponse:
        prompt = _format_prompt(request)
        body = json.dumps(self.request_body(request, prompt=prompt)).encode("utf-8")
        http_request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        content = str(raw.get("response", "")).strip()
        raw["_request_config"] = {
            "model": self.model_name,
            "endpoint": self.endpoint,
            "timeout_seconds": self.timeout_seconds,
            "think": self.think,
            "format_mode": self.format_mode,
            "temperature": self.temperature,
            "num_predict": self.num_predict,
        }
        return LLMResponse(content=content, model=self.model_name, raw=raw)

    def request_body(self, request: LLMRequest, *, prompt: str | None = None) -> dict:
        """Build the Ollama payload separately so ablation settings are testable offline."""

        if self.format_mode == "schema":
            if request.action_schema is None:
                raise ValueError("schema format_mode requires request.action_schema")
            response_format: str | dict = request.action_schema
        else:
            response_format = "json"
        body: dict = {
            "model": self.model_name,
            "prompt": prompt if prompt is not None else _format_prompt(request),
            "stream": False,
            "format": response_format,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }
        if self.think is not None:
            body["think"] = self.think
        return body


def _format_prompt(request: LLMRequest) -> str:
    return (
        "You are a browser automation agent. Return exactly one JSON action.\n"
        "Do not include markdown, commentary, or multiple actions.\n"
        "Return a compact object with only these keys: action, target, value, reason, risk_level, metadata.\n"
        "Use double-quoted JSON strings. Omit keys that are not needed.\n"
        "Keep reason under 12 words.\n"
        "Use the selector value exactly as it appears in an observation selector line.\n"
        "Use select only when the observation line says tag: select; use click for buttons or links.\n"
        "Use click for tag: input with type: checkbox. If checked: True already satisfies the task, do not click it again.\n"
        "For tag: select, include a listed option value.\n"
        "If a previous action failed with multiple matches, choose the specific data-testid selector from the error candidates.\n"
        "Never copy long error text into JSON fields.\n"
        "Allowed actions are: observe_page, click, type, select, extract_text, download_file, finish, request_human, refuse.\n"
        "For type actions, include target and value. For click/extract_text/select, include target.\n"
        "Use finish only after the page state proves the task is complete.\n\n"
        "If you changed a form value and the page shows a Save, Apply, or Confirm control, use it before finish.\n"
        "If a previous extract_text result already contains the requested answer, finish with that answer in reason.\n"
        "If the task completion criteria are already satisfied in the observation, return finish immediately.\n\n"
        f"Task:\n{request.task}\n\n"
        f"Observation:\n{request.observation}\n\n"
        "Examples are format-only. Never copy example selectors unless they appear in the observation.\n"
        'Examples:\n{"action":"click","target":"[data-testid=\\"example-open-details\\"]","reason":"open details","risk_level":"low"}\n'
        '{"action":"click","target":"[data-testid=\\"example-save-draft\\"]","reason":"save changes","risk_level":"low"}\n'
        '{"action":"finish","reason":"visible confirmation proves completion","risk_level":"low"}\n\n'
        f"Safety policy:\n{request.safety_policy or 'Use conservative defaults.'}\n"
    )
