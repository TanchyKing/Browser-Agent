"""Smoke test for the browser tool layer.

This script uses a temporary local HTML fixture when no URL is provided. It is
meant to validate the browser executor and trace recorder without depending on
Conversation B's final task pages.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.browser import BrowserAction, MissingBrowserDependency
from src.browser.playwright_executor import PlaywrightBrowserExecutor
from src.tracing import TraceRecorder


TEMP_FIXTURE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Browser Smoke Fixture</title>
</head>
<body>
  <h1>Browser Smoke Fixture</h1>
  <label for="name">Name</label>
  <input id="name" name="name" />
  <button id="submit" onclick="document.getElementById('status').innerText = 'Submitted: ' + document.getElementById('name').value;">
    Submit
  </button>
  <p id="status">Waiting</p>
</body>
</html>
"""


def build_temp_fixture() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="p3-browser-smoke-"))
    fixture_path = temp_dir / "fixture.html"
    fixture_path.write_text(TEMP_FIXTURE_HTML, encoding="utf-8")
    return fixture_path


def record_action(recorder: TraceRecorder, executor: PlaywrightBrowserExecutor, action: BrowserAction) -> None:
    started = time.perf_counter()
    result = executor.execute(action)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    recorder.record_result(result, elapsed_ms=elapsed_ms)
    if not result.ok:
        prefix = f"{result.error_type}: " if result.error_type else ""
        raise RuntimeError(prefix + (result.error or f"Action failed: {action.name}"))


def run_smoke(target: str | None, trace_out: Path) -> None:
    fixture_path = Path(target) if target else build_temp_fixture()
    if trace_out.exists():
        trace_out.unlink()
    recorder = TraceRecorder(trace_out)
    with PlaywrightBrowserExecutor(headless=True) as executor:
        opened = executor.open(fixture_path)
        recorder.record_result(
            executor.execute(BrowserAction(name="observe_page")),
            metadata={"opened_title": opened.title},
        )
        record_action(recorder, executor, BrowserAction(name="type", selector="#name", text="Codex"))
        record_action(recorder, executor, BrowserAction(name="click", selector="#submit"))
        record_action(recorder, executor, BrowserAction(name="extract_text", selector="#status"))

    rows = recorder.read_steps()
    if not rows or rows[-1].get("extracted_text") != "Submitted: Codex":
        raise RuntimeError("Smoke trace did not capture expected submitted status")
    if [row.get("step_index") for row in rows] != list(range(len(rows))):
        raise RuntimeError("Smoke trace step_index values are not 0-based and contiguous")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run browser tool smoke test")
    parser.add_argument("--url", help="Optional URL or local HTML file. Defaults to a temporary fixture.")
    parser.add_argument(
        "--trace-out",
        default=str(Path(tempfile.gettempdir()) / "p3_browser_smoke_trace.jsonl"),
        help="Trace JSONL output path. Defaults to the system temp directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_smoke(args.url, Path(args.trace_out))
    except MissingBrowserDependency as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK: browser smoke passed; trace written to {args.trace_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
