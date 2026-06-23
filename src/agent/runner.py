"""Agent execution loop skeleton.

The runner depends on narrow protocols so Conversation D can be tested before
the browser-tool lane provides a real Playwright implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from src.agent.actions import AgentAction
from src.agent.safety import SafetyDecision, SafetyPolicy
from src.llm import BaseLLMAdapter, LLMRequest


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
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        if max_recovery_attempts < 0:
            raise ValueError("max_recovery_attempts must be >= 0")
        if max_json_retries < 0:
            raise ValueError("max_json_retries must be >= 0")
        self.llm = llm
        self.tools = tools
        self.safety_policy = safety_policy or SafetyPolicy()
        self.max_steps = max_steps
        self.max_recovery_attempts = max_recovery_attempts
        self.max_json_retries = max_json_retries
        self.action_schema = action_schema
        self.safety_policy_text = safety_policy_text
        self.forbidden_actions = list(forbidden_actions or [])

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
        while attempts <= self.max_json_retries:
            attempts += 1
            llm_response = self.llm.complete(
                LLMRequest(
                    task=task,
                    observation=request_observation,
                    action_schema=self.action_schema,
                    safety_policy=self.safety_policy_text,
                    step_index=step_index,
                )
            )
            try:
                action = AgentAction.from_mapping(llm_response.as_json())
            except Exception as exc:
                last_error = str(exc)
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
                        ),
                        request_observation,
                    )
                request_observation = _with_json_retry_context(observation, last_error, attempts)
                continue
            return (
                action,
                _llm_result(
                    attempts=attempts,
                    first_valid=attempts == 1,
                    after_retry_valid=True,
                    retry_success=attempts > 1,
                    error=None,
                    first_error=first_error,
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
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "json_attempts": attempts,
        "json_first_valid": first_valid,
        "json_after_retry_valid": after_retry_valid,
        "json_retried": attempts > 1,
        "json_retry_success": retry_success,
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
    ]:
        if key in llm_result:
            merged[key] = llm_result[key]
    return merged
