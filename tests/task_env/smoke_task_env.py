"""Smoke checks for the offline task fixtures.

This intentionally avoids Playwright and external dependencies. It verifies that
the task records are parseable, local-only, and refer to existing fixture pages
and DOM ids. Browser execution belongs to Conversation C.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TASK_FILE = ROOT / "tasks" / "offline_tasks.jsonl"
WEB_TASKS = ROOT / "web" / "tasks"
ACTION_SCHEMA = ROOT / "configs" / "schema" / "action.schema.json"

SUPPORTED_SUCCESS_CHECKS = {
    ("scripted_dom", "element_text"),
    ("file_exists", "download_name"),
    ("static_dom", "element_exists"),
    ("static_dom", "extracted_text_contains"),
    ("agent_terminal", "terminal_action"),
    ("agent_terminal", "forbidden_action_not_executed"),
}

PENDING_SUCCESS_CHECKS = {
    ("safety_event", "safety_event_type"),
    ("safety_event", "forbidden_action_not_executed"),
}

REQUIRED_FIELDS = {
    "task_id",
    "category",
    "difficulty",
    "instruction",
    "start_url",
    "allowed_actions",
    "forbidden_actions",
    "expected_state",
    "success_check",
}


def load_tasks() -> list[dict]:
    tasks: list[dict] = []
    for line_no, line in enumerate(TASK_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            task = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"Invalid JSON on line {line_no}: {exc}") from exc
        missing = REQUIRED_FIELDS - set(task)
        if missing:
            raise AssertionError(f"{task.get('task_id', line_no)} missing fields: {sorted(missing)}")
        tasks.append(task)
    return tasks


def collect_dom_ids() -> set[str]:
    ids: set[str] = set()
    for html_file in WEB_TASKS.glob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        ids.update(re.findall(r'id="([^"]+)"', text))
    return ids


def collect_testids() -> set[str]:
    testids: set[str] = set()
    for html_file in WEB_TASKS.glob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        testids.update(re.findall(r'data-testid="([^"]+)"', text))
    return testids


def load_action_enum() -> set[str]:
    schema = json.loads(ACTION_SCHEMA.read_text(encoding="utf-8"))
    return set(schema["properties"]["action"]["enum"])


def selector_id(selector: str) -> str | None:
    if not selector.startswith("#"):
        return None
    value = selector[1:]
    if value.endswith(".clicked"):
        return None
    return value


def selector_testid(selector: str) -> str | None:
    match = re.fullmatch(r"\[data-testid='([^']+)'\]", selector)
    if match:
        return match.group(1)
    match = re.fullmatch(r'\[data-testid="([^"]+)"\]', selector)
    if match:
        return match.group(1)
    return None


def check_selector(selector: str, dom_ids: set[str], testids: set[str], task_id: str) -> None:
    sid = selector_id(selector)
    if sid and sid not in dom_ids:
        raise AssertionError(f"{task_id} references missing selector {selector}")
    testid = selector_testid(selector)
    if testid and testid not in testids:
        raise AssertionError(f"{task_id} references missing data-testid selector {selector}")


def check_success_support(task: dict, mode: str, kind: str, support_status: str) -> None:
    task_id = task["task_id"]
    pair = (mode, kind)
    if support_status == "current_eval":
        if pair not in SUPPORTED_SUCCESS_CHECKS:
            raise AssertionError(
                f"{task_id} marks unsupported success check {pair} as current_eval"
            )
    elif support_status == "pending_eval_integration":
        if pair not in PENDING_SUCCESS_CHECKS:
            raise AssertionError(
                f"{task_id} marks unknown pending success check {pair}"
            )
    else:
        raise AssertionError(f"{task_id} invalid support_status: {support_status}")


def main() -> None:
    tasks = load_tasks()
    if len(tasks) < 10:
        raise AssertionError(f"Expected at least 10 tasks, got {len(tasks)}")

    dom_ids = collect_dom_ids()
    testids = collect_testids()
    action_enum = load_action_enum()
    task_ids = set()
    categories = set()

    for task in tasks:
        task_id = task["task_id"]
        if task_id in task_ids:
            raise AssertionError(f"Duplicate task_id: {task_id}")
        task_ids.add(task_id)
        categories.add(task["category"])

        start_url = task["start_url"]
        if not start_url.startswith("web/tasks/"):
            raise AssertionError(f"{task_id} uses non-local start_url: {start_url}")
        start_path = ROOT / start_url
        if not start_path.exists():
            raise AssertionError(f"{task_id} start_url does not exist: {start_url}")

        if not isinstance(task["forbidden_actions"], list):
            raise AssertionError(f"{task_id} forbidden_actions must be a list")
        if "ask_user" in task["allowed_actions"]:
            raise AssertionError(f"{task_id} uses deprecated action alias ask_user")
        if not set(task["allowed_actions"]).issubset(action_enum):
            unknown = sorted(set(task["allowed_actions"]) - action_enum)
            raise AssertionError(f"{task_id} allowed_actions not in action schema enum: {unknown}")

        for section in (task["expected_state"], task["success_check"]):
            checks = section.get("checks") or section.get("all_of") or []
            if not checks:
                raise AssertionError(f"{task_id} has no checks in {section}")
            for check in checks:
                target = check.get("target", "")
                if target not in {"download", "agent_answer", "agent.action"}:
                    check_selector(target, dom_ids, testids, task_id)

        success_check = task["success_check"]
        mode = success_check.get("mode")
        support_status = success_check.get("support_status")
        for check in success_check.get("all_of", []):
            check_success_support(task, mode, check.get("kind"), support_status)

        for forbidden in task["forbidden_actions"]:
            selector = forbidden.get("selector")
            if selector:
                check_selector(selector, dom_ids, testids, task_id)

    safety_tasks = [task for task in tasks if task["difficulty"] == "safety"]
    if len(safety_tasks) < 2:
        raise AssertionError("Expected at least two safety tasks")

    print(f"tasks={len(tasks)} categories={len(categories)} safety_tasks={len(safety_tasks)}")


if __name__ == "__main__":
    main()
