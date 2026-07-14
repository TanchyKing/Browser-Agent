"""Agent execution loop skeleton.

The runner depends on narrow protocols so Conversation D can be tested before
the browser-tool lane provides a real Playwright implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.agent.actions import AgentAction
from src.agent.safety import SafetyDecision, SafetyPolicy
from src.llm import (
    BaseLLMAdapter,
    LLMRequest,
    LLMResponse,
    observation_candidates,
    observation_grounded_schema,
    validate_structured_action,
)


class BrowserTools(Protocol):
    def observe_page(self) -> str:
        """Return a text observation of the current browser state."""

    def execute(self, action: AgentAction) -> dict[str, Any]:
        """Execute a validated, safe action and return a structured result."""


@dataclass(frozen=True)
class AgentStep:
    step_index: int
    observation: str
    action: AgentAction | None
    safety: SafetyDecision
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    recovery_attempt: bool = False
    recovery_success: bool = False


@dataclass(frozen=True)
class AgentRunResult:
    completed: bool
    terminal_action: str | None
    steps: tuple[AgentStep, ...]


class BrowserAgentRunner:
    def __init__(
        self,
        llm: BaseLLMAdapter,
        tools: BrowserTools,
        safety_policy: SafetyPolicy | None = None,
        max_steps: int = 8,
        max_recovery_attempts: int = 2,
        max_json_retries: int = 1,
        action_schema: dict[str, Any] | None = None,
        safety_policy_text: str | None = None,
        forbidden_actions: list[dict[str, Any]] | None = None,
        raw_response_preview_chars: int = 8192,
        request_preview_chars: int = 32768,
        structured_validation: bool = False,
        dynamic_selector_enum: bool = False,
        retry_prompt_mode: str = "legacy",
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        if max_recovery_attempts < 0:
            raise ValueError("max_recovery_attempts must be >= 0")
        if max_json_retries < 0:
            raise ValueError("max_json_retries must be >= 0")
        if retry_prompt_mode not in {"legacy", "bounded"}:
            raise ValueError("retry_prompt_mode must be 'legacy' or 'bounded'")
        self.llm = llm
        self.tools = tools
        self.safety_policy = safety_policy or SafetyPolicy()
        self.max_steps = max_steps
        self.max_recovery_attempts = max_recovery_attempts
        self.max_json_retries = max_json_retries
        self.action_schema = action_schema
        self.safety_policy_text = safety_policy_text
        self.forbidden_actions = list(forbidden_actions or [])
        self.raw_response_preview_chars = raw_response_preview_chars
        self.request_preview_chars = request_preview_chars
        self.structured_validation = structured_validation
        self.dynamic_selector_enum = dynamic_selector_enum
        self.retry_prompt_mode = retry_prompt_mode

    def run(self, task: str) -> AgentRunResult:
        steps: list[AgentStep] = []
        recovery_context: str | None = None
        recovery_attempts = 0
        last_successful_action: tuple[str, str | None, str | int | float | bool | None] | None = None
        repeated_successful_actions = 0
        repeat_feedbacks = 0
        for step_index in range(self.max_steps):
            base_observation = self.tools.observe_page()
            observation = _with_recovery_context(base_observation, recovery_context)
            action, llm_result, observation = self._complete_action(task, observation, step_index)
            if action is None:
                steps.append(
                    AgentStep(
                        step_index=step_index,
                        observation=observation,
                        action=None,
                        safety=SafetyDecision(False, False, "invalid llm response"),
                        result=llm_result,
                        error=str(llm_result.get("error") or "invalid llm response"),
                    )
                )
                return AgentRunResult(False, None, tuple(steps))

            safety = self.safety_policy.evaluate(
                action,
                page_text=base_observation,
                forbidden_actions=self.forbidden_actions,
            )
            if not safety.allowed:
                result = _with_llm_result({}, llm_result)
                steps.append(
                    AgentStep(
                        step_index=step_index,
                        observation=observation,
                        action=action,
                        safety=safety,
                        result=result,
                        error=safety.reason,
                    )
                )
                return AgentRunResult(False, action.action, tuple(steps))

            if action.is_terminal:
                result = _with_llm_result({"terminal": action.action}, llm_result)
                if action.action == "request_human":
                    result.update(
                        {
                            "handoff": True,
                            "requires_human": True,
                            "handoff_reason": action.reason,
                            "requested_input": action.metadata.get("requested_input"),
                        }
                    )
                steps.append(
                    AgentStep(
                        step_index=step_index,
                        observation=observation,
                        action=action,
                        safety=safety,
                        result=result,
                    )
                )
                return AgentRunResult(True, action.action, tuple(steps))

            try:
                result = _with_llm_result(_normalize_execute_result(self.tools.execute(action)), llm_result)
            except Exception as exc:
                result = _with_llm_result(
                    {"ok": False, "error": str(exc), "error_type": type(exc).__name__},
                    llm_result,
                )

            error = _execution_error(result)
            is_recoverable = error is not None and _is_recoverable_error(error)
            should_retry = is_recoverable and recovery_attempts < self.max_recovery_attempts
            steps.append(
                AgentStep(
                    step_index=step_index,
                    observation=observation,
                    action=action,
                    safety=safety,
                    result=result,
                    error=error,
                    recovery_attempt=bool(should_retry),
                )
            )
            if error:
                last_successful_action = None
                repeated_successful_actions = 0
                if should_retry:
                    recovery_attempts += 1
                    recovery_context = _format_recovery_context(action, result, recovery_attempts)
                    continue
                return AgentRunResult(False, action.action, tuple(steps))
            action_signature = _action_signature(action)
            if action_signature == last_successful_action:
                repeated_successful_actions += 1
            else:
                last_successful_action = action_signature
                repeated_successful_actions = 1
            if recovery_attempts:
                previous = steps[-1]
                steps[-1] = AgentStep(
                    step_index=previous.step_index,
                    observation=previous.observation,
                    action=previous.action,
                    safety=previous.safety,
                    result=previous.result,
                    error=previous.error,
                    recovery_attempt=previous.recovery_attempt,
                    recovery_success=True,
                )
                recovery_attempts = 0
            if (
                repeated_successful_actions >= 2
                and repeat_feedbacks < self.max_recovery_attempts
            ):
                repeat_feedbacks += 1
                recovery_context = _format_repeat_context(action, repeated_successful_actions, repeat_feedbacks)
                continue
            success_context = _format_success_context(action, result)
            if success_context:
                recovery_context = success_context
                continue
            recovery_context = None

        return AgentRunResult(False, None, tuple(steps))

    def _complete_action(
        self,
        task: str,
        observation: str,
        step_index: int,
    ) -> tuple[AgentAction | None, dict[str, Any], str]:
        attempts = 0
        request_observation = observation
        first_error: str | None = None
        last_error: str | None = None
        attempt_audits: list[dict[str, Any]] = []
        while attempts <= self.max_json_retries:
            attempts += 1
            request_schema = self.action_schema
            selector_candidates, option_candidates = observation_candidates(request_observation)
            candidate_snapshot = {
                "selectors": selector_candidates,
                "select_options": option_candidates,
            }
            if self.dynamic_selector_enum and self.action_schema is not None:
                request_schema, candidate_snapshot = observation_grounded_schema(
                    self.action_schema,
                    request_observation,
                )
            request_task = task
            if attempts > 1 and self.retry_prompt_mode == "bounded":
                request_task = _short_task_summary(task)
            llm_request = LLMRequest(
                task=request_task,
                observation=request_observation,
                action_schema=request_schema,
                candidate_snapshot=candidate_snapshot,
                safety_policy=self.safety_policy_text,
                step_index=step_index,
            )
            llm_response = self.llm.complete(llm_request)
            try:
                action_payload = llm_response.as_json()
                if self.structured_validation:
                    action_payload = validate_structured_action(action_payload)
                action = AgentAction.from_mapping(action_payload)
            except Exception as exc:
                last_error = str(exc)
                attempt_audits.append(
                    _llm_attempt_audit(
                        attempt=attempts,
                        request=llm_request,
                        response=llm_response,
                        parse_valid=False,
                        parse_error=last_error,
                        request_preview_chars=self.request_preview_chars,
                        raw_response_preview_chars=self.raw_response_preview_chars,
                    )
                )
                if first_error is None:
                    first_error = last_error
                if attempts > self.max_json_retries:
                    return (
                        None,
                        _llm_result(
                            attempts=attempts,
                            first_valid=False,
                            after_retry_valid=False,
                            retry_success=False,
                            error=last_error,
                            first_error=first_error,
                            attempt_audits=attempt_audits,
                        ),
                        request_observation,
                    )
                if self.retry_prompt_mode == "bounded":
                    request_observation = _with_bounded_json_retry_context(
                        observation,
                        last_error,
                        attempts,
                    )
                else:
                    request_observation = _with_json_retry_context(observation, last_error, attempts)
                continue
            attempt_audits.append(
                _llm_attempt_audit(
                    attempt=attempts,
                    request=llm_request,
                    response=llm_response,
                    parse_valid=True,
                    parse_error=None,
                    request_preview_chars=self.request_preview_chars,
                    raw_response_preview_chars=self.raw_response_preview_chars,
                )
            )
            return (
                action,
                _llm_result(
                    attempts=attempts,
                    first_valid=attempts == 1,
                    after_retry_valid=True,
                    retry_success=attempts > 1,
                    error=None,
                    first_error=first_error,
                    attempt_audits=attempt_audits,
                ),
                request_observation,
            )


def _normalize_execute_result(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    result: dict[str, Any] = {}
    for field_name in ["ok", "error", "error_type", "extracted_text", "download_path", "metadata"]:
        if hasattr(raw, field_name):
            result[field_name] = getattr(raw, field_name)
    if hasattr(raw, "action"):
        result["action"] = str(getattr(raw, "action"))
    if "ok" not in result:
        result["ok"] = True
    return result


def _execution_error(result: dict[str, Any]) -> str | None:
    ok = bool(result.get("ok", True))
    error = result.get("error")
    if not ok:
        return str(error or "browser action failed")
    return None


def _is_recoverable_error(error: str) -> bool:
    lowered = error.lower()
    return any(
        marker in lowered
        for marker in [
            "strict mode",
            "resolved to",
            "element not found",
            "not found",
            "timeout",
            "waiting for locator",
        ]
    )


def _with_recovery_context(observation: str, recovery_context: str | None) -> str:
    if not recovery_context:
        return observation
    return f"{observation}\n\nAction feedback for next turn:\n{recovery_context}"


def _with_json_retry_context(observation: str, error: str, attempt: int) -> str:
    return (
        f"{observation}\n\n"
        "JSON correction feedback:\n"
        f"json_retry_attempt={attempt}\n"
        f"invalid_json_error={error}\n"
        "Return exactly one compact valid JSON object. Do not include markdown, comments, or copied page text."
    )


def _with_bounded_json_retry_context(observation: str, error: str, attempt: int) -> str:
    selector_lines = [
        line.strip()
        for line in observation.splitlines()
        if line.strip().startswith("- selector: ")
    ]
    selectors = "\n".join(selector_lines[:100]) or "- no grounded selector available"
    return (
        "Bounded JSON correction context (page prose intentionally omitted):\n"
        f"json_retry_attempt={attempt}\n"
        f"validation_error={error[:500]}\n"
        "Available grounded elements:\n"
        f"{selectors}\n"
        "Return exactly one compact object matching the supplied action schema. "
        "Do not copy page prose or error text into any field."
    )


def _short_task_summary(task: str, max_chars: int = 500) -> str:
    compact = " ".join(task.split())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rsplit(" ", 1)[0] + "…"


def _format_recovery_context(action: AgentAction, result: dict[str, Any], attempt: int) -> str:
    pieces = [
        "Previous action failed. Use this error feedback to choose a more specific selector.",
        f"recovery_attempt={attempt}",
        f"failed_action={action.action}",
        f"failed_target={action.target}",
        f"error={result.get('error')}",
    ]
    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        candidates = metadata.get("candidate_elements") or metadata.get("candidates")
        if candidates:
            pieces.append(f"candidate_elements={candidates}")
    return "\n".join(piece for piece in pieces if piece)


def _action_signature(action: AgentAction) -> tuple[str, str | None, str | int | float | bool | None]:
    return (action.action, action.target, action.value)


def _format_repeat_context(action: AgentAction, repeat_count: int, feedback_count: int) -> str:
    pieces = [
        "Repeated successful action detected. Choose a different next action, or finish/request_human if the task is complete.",
        f"repeat_feedback={feedback_count}",
        f"repeated_action={action.action}",
        f"repeated_target={action.target}",
        f"repeated_value={action.value}",
        f"repeat_count={repeat_count}",
    ]
    return "\n".join(piece for piece in pieces if piece)


def _format_success_context(action: AgentAction, result: dict[str, Any]) -> str | None:
    if action.action == "extract_text" and result.get("extracted_text"):
        return "\n".join(
            [
                "Previous tool action succeeded.",
                "last_action=extract_text",
                f"last_target={action.target}",
                f"extracted_text={result.get('extracted_text')}",
                "If this text satisfies the task, return finish and include the needed answer in reason.",
            ]
        )
    if action.action == "download_file" and result.get("download_path"):
        return "\n".join(
            [
                "Previous tool action succeeded.",
                "last_action=download_file",
                f"download_path={result.get('download_path')}",
                "If the download satisfies the task, return finish.",
            ]
        )
    return None


def _llm_result(
    *,
    attempts: int,
    first_valid: bool,
    after_retry_valid: bool,
    retry_success: bool,
    error: str | None,
    first_error: str | None,
    attempt_audits: list[dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "json_attempts": attempts,
        "json_first_valid": first_valid,
        "json_after_retry_valid": after_retry_valid,
        "json_retried": attempts > 1,
        "json_retry_success": retry_success,
        "llm_attempts": attempt_audits,
    }
    if error:
        result["error"] = error
        result["error_type"] = "invalid_llm_response"
    if first_error:
        result["json_first_error"] = first_error
    return result


def _with_llm_result(result: dict[str, Any], llm_result: dict[str, Any]) -> dict[str, Any]:
    merged = dict(result)
    for key in [
        "json_attempts",
        "json_first_valid",
        "json_after_retry_valid",
        "json_retried",
        "json_retry_success",
        "json_first_error",
        "llm_attempts",
    ]:
        if key in llm_result:
            merged[key] = llm_result[key]
    return merged


def _llm_attempt_audit(
    *,
    attempt: int,
    request: LLMRequest,
    response: LLMResponse,
    parse_valid: bool,
    parse_error: str | None,
    request_preview_chars: int,
    raw_response_preview_chars: int,
) -> dict[str, Any]:
    raw = response.raw if isinstance(response.raw, dict) else {}
    schema_json = (
        json.dumps(request.action_schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if request.action_schema is not None
        else ""
    )
    thinking = str(raw.get("thinking") or "")
    done_reason = raw.get("done_reason")
    audit: dict[str, Any] = {
        "attempt": attempt,
        "request": {
            "step_index": request.step_index,
            "task_preview": _redacted_preview(request.task, request_preview_chars),
            "task_chars": len(request.task),
            "task_sha256": _sha256_text(request.task),
            "observation_preview": _redacted_preview(request.observation, request_preview_chars),
            "observation_chars": len(request.observation),
            "observation_sha256": _sha256_text(request.observation),
            "action_schema": request.action_schema,
            "action_schema_sha256": _sha256_text(schema_json) if schema_json else None,
            "candidate_snapshot": request.candidate_snapshot,
            "safety_policy_preview": _redacted_preview(
                request.safety_policy or "",
                request_preview_chars,
            ),
        },
        "response": {
            "model": response.model,
            "raw_response_preview": _redacted_preview(response.content, raw_response_preview_chars),
            "raw_response_chars": len(response.content),
            "raw_response_sha256": _sha256_text(response.content),
            "thinking_preview": _redacted_preview(thinking, raw_response_preview_chars),
            "thinking_chars": len(thinking),
            "thinking_sha256": _sha256_text(thinking) if thinking else None,
            "done": raw.get("done"),
            "done_reason": done_reason,
            "truncated": done_reason == "length" or raw.get("done") is False,
            "prompt_eval_count": raw.get("prompt_eval_count"),
            "eval_count": raw.get("eval_count"),
            "prompt_eval_duration": raw.get("prompt_eval_duration"),
            "eval_duration": raw.get("eval_duration"),
            "total_duration": raw.get("total_duration"),
            "load_duration": raw.get("load_duration"),
        },
        "parse_valid": parse_valid,
        "parse_error": parse_error,
    }
    request_config = raw.get("_request_config")
    audit["request"]["inference"] = (
        dict(request_config) if isinstance(request_config, dict) else {"model": response.model}
    )
    audit["parse_error_position"] = _json_error_position(parse_error)
    return audit


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redacted_preview(value: str, max_chars: int) -> str:
    redacted = re.sub(
        r"(?i)\b(password|token|secret|api[_-]?key|authorization)(\s*[:=]\s*)([^\s,;]+)",
        r"\1\2<redacted>",
        value,
    )
    redacted = re.sub(
        r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "<redacted-email>",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\bfile:///(?:[^\s]+)",
        "file:///<redacted-local-path>",
        redacted,
    )
    if max_chars == 0:
        return ""
    if len(redacted) <= max_chars:
        return redacted
    head_chars = max_chars // 2
    tail_chars = max_chars - head_chars
    omitted = len(redacted) - max_chars
    return redacted[:head_chars] + f"\n<truncated {omitted} chars>\n" + redacted[-tail_chars:]


def _json_error_position(error: str | None) -> int | None:
    if not error:
        return None
    match = re.search(r"\bchar\s+(\d+)\b", error)
    return int(match.group(1)) if match else None
