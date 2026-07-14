"""Versioned experiment configuration and frozen suite manifests.

The defaults intentionally reproduce the Phase 1 inference path. Phase 2
ablations opt into one behavior change at a time through a checked-in config.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class InferenceConfig:
    model_name: str = "qwen3:8b"
    endpoint: str = "http://localhost:11434/api/generate"
    timeout_seconds: int = 180
    think: bool | None = None
    format_mode: str = "json"
    temperature: float = 0.0
    num_predict: int = 768
    action_schema_path: str = "configs/schema/action.schema.json"
    structured_validation: bool = False
    dynamic_selector_enum: bool = False
    retry_prompt_mode: str = "legacy"

    def __post_init__(self) -> None:
        if self.timeout_seconds < 1:
            raise ValueError("inference.timeout_seconds must be >= 1")
        if self.format_mode not in {"json", "schema"}:
            raise ValueError("inference.format_mode must be 'json' or 'schema'")
        if self.num_predict < 1:
            raise ValueError("inference.num_predict must be >= 1")
        if self.retry_prompt_mode not in {"legacy", "bounded"}:
            raise ValueError("inference.retry_prompt_mode must be 'legacy' or 'bounded'")


@dataclass(frozen=True)
class RunnerConfig:
    max_steps: int = 8
    max_recovery_attempts: int = 2
    max_json_retries: int = 1

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("runner.max_steps must be >= 1")
        if self.max_recovery_attempts < 0:
            raise ValueError("runner.max_recovery_attempts must be >= 0")
        if self.max_json_retries < 0:
            raise ValueError("runner.max_json_retries must be >= 0")


@dataclass(frozen=True)
class LoggingConfig:
    raw_response_preview_chars: int = 8192
    request_preview_chars: int = 32768

    def __post_init__(self) -> None:
        if self.raw_response_preview_chars < 0:
            raise ValueError("logging.raw_response_preview_chars must be >= 0")
        if self.request_preview_chars < 0:
            raise ValueError("logging.request_preview_chars must be >= 0")


@dataclass(frozen=True)
class EvaluatorConfig:
    grader_version: str = "legacy"
    task_file_path: str = "tasks/offline_tasks.jsonl"
    task_overrides_path: str | None = None

    def __post_init__(self) -> None:
        if self.grader_version not in {"legacy", "v2"}:
            raise ValueError("evaluator.grader_version must be 'legacy' or 'v2'")


@dataclass(frozen=True)
class PromptConfig:
    mode: str = "legacy"

    def __post_init__(self) -> None:
        if self.mode not in {"legacy", "contract"}:
            raise ValueError("prompt.mode must be 'legacy' or 'contract'")


@dataclass(frozen=True)
class ControllerConfig:
    enabled: bool = False
    state_enabled: bool = False
    completion_verifier_enabled: bool = False
    repeat_cooldown_enabled: bool = False
    trust_partition_enabled: bool = False
    critic_enabled: bool = False
    block_recovery_enabled: bool = False
    max_consecutive_blocks: int = 2

    def __post_init__(self) -> None:
        if self.max_consecutive_blocks < 1:
            raise ValueError("controller.max_consecutive_blocks must be >= 1")


@dataclass(frozen=True)
class ExperimentConfig:
    version: int = 1
    experiment_id: str = "phase2-r1-legacy"
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    evaluator: EvaluatorConfig = field(default_factory=EvaluatorConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    source_path: str | None = field(default=None, compare=False)

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        source_path: str | None = None,
    ) -> "ExperimentConfig":
        allowed = {
            "version",
            "experiment_id",
            "inference",
            "runner",
            "logging",
            "evaluator",
            "prompt",
            "controller",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError(f"Unknown experiment config keys: {', '.join(unknown)}")
        return cls(
            version=int(payload.get("version", 1)),
            experiment_id=str(payload.get("experiment_id", "phase2-r1-legacy")),
            inference=InferenceConfig(**dict(payload.get("inference") or {})),
            runner=RunnerConfig(**dict(payload.get("runner") or {})),
            logging=LoggingConfig(**dict(payload.get("logging") or {})),
            evaluator=EvaluatorConfig(**dict(payload.get("evaluator") or {})),
            prompt=PromptConfig(**dict(payload.get("prompt") or {})),
            controller=ControllerConfig(**dict(payload.get("controller") or {})),
            source_path=source_path,
        )

    def values(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("source_path", None)
        return payload

    def digest(self) -> str:
        canonical = json.dumps(
            self.values(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "sha256": self.digest(),
            "values": self.values(),
        }


@dataclass(frozen=True)
class SuiteManifest:
    suite_id: str
    task_ids: tuple[str, ...]
    source_path: str
    sha256: str

    def snapshot(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "task_ids": list(self.task_ids),
            "source_path": self.source_path,
            "sha256": self.sha256,
        }


def load_experiment_config(path: str | Path | None = None) -> ExperimentConfig:
    if path is None:
        return ExperimentConfig()
    config_path = Path(path).resolve()
    raw = config_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Non-JSON YAML config requires PyYAML; install requirements.txt or use JSON-compatible YAML."
            ) from exc
        payload = yaml.safe_load(raw)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("Experiment config root must be a mapping")
    extends = payload.pop("extends", None)
    if extends:
        parent_path = Path(str(extends))
        if not parent_path.is_absolute():
            parent_path = config_path.parent / parent_path
        parent = load_experiment_config(parent_path).values()
        payload = _deep_merge(parent, payload)
    return ExperimentConfig.from_mapping(payload, source_path=str(config_path))


def load_suite_manifest(path: str | Path) -> SuiteManifest:
    manifest_path = Path(path).resolve()
    raw = manifest_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Suite manifest root must be an object")
    suite_id = str(payload.get("suite_id") or manifest_path.stem)
    raw_task_ids = payload.get("task_ids")
    if not isinstance(raw_task_ids, list) or not raw_task_ids:
        raise ValueError("Suite manifest task_ids must be a non-empty list")
    task_ids = tuple(str(task_id) for task_id in raw_task_ids)
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("Suite manifest contains duplicate task ids")
    return SuiteManifest(
        suite_id=suite_id,
        task_ids=task_ids,
        source_path=str(manifest_path),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = value
    return merged
