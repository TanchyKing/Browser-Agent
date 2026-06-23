"""Environment readiness checks for the local Browser Agent project.

This script only inspects the local machine. It does not install packages,
download browsers, start services, or call external APIs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str
    command: str | None = None


def run_command(command: list[str], timeout: int = 10) -> tuple[int | None, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None, "command not found"
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"

    output = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode, output


def first_line(text: str) -> str:
    return text.splitlines()[0].strip() if text else ""


def check_python() -> CheckResult:
    version = sys.version.replace("\n", " ")
    executable = sys.executable
    detail = f"{version}; executable={executable}"
    status = "ok" if sys.version_info >= (3, 11) else "warn"
    if status == "warn":
        detail += "; Python 3.11+ is recommended"
    return CheckResult("python", status, detail)


def check_platform() -> CheckResult:
    detail = f"{platform.platform()}; cwd={Path.cwd()}"
    return CheckResult("platform", "ok", detail)


def check_memory_hint() -> CheckResult:
    # Avoid extra dependencies such as psutil. This is a lightweight hint only.
    processor = platform.processor() or "unknown"
    return CheckResult("system_hint", "info", f"processor={processor}")


def check_executable(name: str, version_args: Iterable[str]) -> CheckResult:
    exe = shutil.which(name)
    if not exe:
        return CheckResult(name, "missing", f"{name} not found on PATH")
    command = [exe, *version_args]
    code, output = run_command(command)
    if code == 0:
        return CheckResult(name, "ok", f"{exe}; {first_line(output)}", " ".join(command))
    return CheckResult(name, "warn", f"{exe}; version check failed: {first_line(output)}", " ".join(command))


def check_python_package(import_name: str, label: str | None = None) -> CheckResult:
    label = label or import_name
    spec = importlib.util.find_spec(import_name)
    if spec is None:
        return CheckResult(label, "missing", f"Python package '{import_name}' is not importable")
    origin = spec.origin or "namespace package"
    return CheckResult(label, "ok", origin)


def check_python_playwright_cli() -> CheckResult:
    spec = importlib.util.find_spec("playwright")
    if spec is None:
        return CheckResult("python_playwright_cli", "missing", "Python Playwright is not installed")
    code, output = run_command([sys.executable, "-m", "playwright", "--version"])
    if code == 0:
        return CheckResult(
            "python_playwright_cli",
            "ok",
            first_line(output),
            f"{sys.executable} -m playwright --version",
        )
    return CheckResult(
        "python_playwright_cli",
        "warn",
        f"Playwright importable, CLI failed: {first_line(output)}",
        f"{sys.executable} -m playwright --version",
    )


def check_node_playwright() -> CheckResult:
    npx = shutil.which("npx")
    if not npx:
        return CheckResult("node_playwright", "missing", "npx not found on PATH")
    code, output = run_command([npx, "playwright", "--version"], timeout=15)
    if code == 0:
        return CheckResult("node_playwright", "ok", first_line(output), f"{npx} playwright --version")
    return CheckResult(
        "node_playwright",
        "missing",
        f"Node Playwright CLI unavailable: {first_line(output)}",
        f"{npx} playwright --version",
    )


def check_browser_runtime() -> CheckResult:
    candidates = [
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH"),
        str(Path.home() / "AppData" / "Local" / "ms-playwright"),
        str(Path.home() / ".cache" / "ms-playwright"),
    ]
    existing = [path for path in candidates if path and Path(path).exists()]
    if existing:
        return CheckResult("playwright_browsers", "ok", "; ".join(existing))
    return CheckResult(
        "playwright_browsers",
        "missing",
        "No local Playwright browser runtime directory found in common locations",
    )


def check_ollama() -> list[CheckResult]:
    ollama = shutil.which("ollama")
    if not ollama:
        return [CheckResult("ollama", "missing", "ollama not found on PATH")]

    results = [CheckResult("ollama", "ok", ollama)]
    code, output = run_command([ollama, "list"], timeout=15)
    if code != 0:
        results.append(CheckResult("ollama_models", "warn", f"ollama list failed: {first_line(output)}", f"{ollama} list"))
        return results

    has_qwen = "qwen3:8b" in output.lower()
    status = "ok" if has_qwen else "missing"
    detail = "qwen3:8b found" if has_qwen else "qwen3:8b not found in ollama list"
    results.append(CheckResult("ollama_qwen3_8b", status, detail, f"{ollama} list"))
    return results


def collect_results() -> list[CheckResult]:
    results = [
        check_python(),
        check_platform(),
        check_memory_hint(),
        check_executable("node", ["--version"]),
        check_executable("npm", ["--version"]),
        check_executable("npx", ["--version"]),
        check_python_package("playwright", "python_playwright"),
        check_python_playwright_cli(),
        check_node_playwright(),
        check_browser_runtime(),
    ]
    results.extend(check_ollama())
    return results


def print_text(results: list[CheckResult]) -> None:
    print("P3 Browser Agent environment check")
    print("=" * 36)
    for result in results:
        command = f" [{result.command}]" if result.command else ""
        print(f"{result.status.upper():8} {result.name}: {result.detail}{command}")

    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    print("-" * 36)
    print("Summary:", ", ".join(f"{key}={counts[key]}" for key in sorted(counts)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local Browser Agent project environment.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    results = collect_results()
    if args.json:
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
    else:
        print_text(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
