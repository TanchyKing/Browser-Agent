"""JSONL trace recorder for browser-agent runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.browser import BrowserActionResult


@dataclass(frozen=True)
class TraceStep:
    """One auditable browser-agent step."""

    run_id: str
    step_index: int
    timestamp_utc: str
    action: dict[str, Any]
    ok: bool
    observation: dict[str, Any] | None = None
    extracted_text: str | None = None
    download_path: str | None = None
    error_type: str | None = None
    error: str | None = None
    elapsed_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TraceRecorder:
    """Append-only JSONL recorder.

    The recorder deliberately writes one compact object per step so later
    evaluation and dashboard code can stream traces without loading a database.
    """

    def __init__(self, output_path: str | Path, *, run_id: str | None = None) -> None:
        self.output_path = Path(output_path)
        self.run_id = run_id or str(uuid4())
        self.step_index = 0
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def record_result(
        self,
        result: BrowserActionResult,
        *,
        elapsed_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceStep:
        """Record one browser action result and return the serialized step."""

        current_step_index = self.step_index
        observation = _summarize_observation(result.observation)
        step = TraceStep(
            run_id=self.run_id,
            step_index=current_step_index,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            action=asdict(result.action),
            ok=result.ok,
            observation=observation,
            extracted_text=result.extracted_text,
            download_path=result.download_path,
            error_type=result.error_type,
            error=result.error,
            elapsed_ms=elapsed_ms,
            metadata={**result.metadata, **(metadata or {})},
        )
        with self.output_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(step), ensure_ascii=False, sort_keys=True) + "\n")
        self.step_index += 1
        return step

    def read_steps(self) -> list[dict[str, Any]]:
        """Read the current JSONL trace file."""

        if not self.output_path.exists():
            return []
        with self.output_path.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


def _summarize_observation(observation: Any | None) -> dict[str, Any] | None:
    """Keep trace observations compact while preserving grounding evidence."""

    if observation is None:
        return None

    elements = []
    for element in observation.elements[:20]:
        elements.append(
            {
                key: element.get(key)
                for key in (
                    "index",
                    "tag",
                    "text",
                    "selector",
                    "selector_strategy",
                    "selector_unique",
                    "options",
                    "download",
                    "href",
                    "id",
                    "name",
                    "testid",
                    "type",
                )
                if element.get(key) not in (None, "")
            }
        )

    text = observation.text or ""
    return {
        "url": observation.url,
        "title": observation.title,
        "text_excerpt": text[:1000],
        "elements": elements,
        "screenshot_path": observation.screenshot_path,
    }
