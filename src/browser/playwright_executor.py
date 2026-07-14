"""Playwright-backed browser executor.

The import of Playwright is intentionally lazy so the rest of the project can
run tests and static checks before Conversation A installs browser dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import re

from .tools import (
    BrowserAction,
    BrowserActionResult,
    BrowserObservation,
    MissingBrowserDependency,
)


class PlaywrightBrowserExecutor:
    """Minimal synchronous Playwright executor for browser tool actions."""

    def __init__(self, *, headless: bool = True, timeout_ms: int = 5000) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None

    def __enter__(self) -> "PlaywrightBrowserExecutor":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def start(self) -> None:
        """Start Playwright and open a browser page."""

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise MissingBrowserDependency(
                "Python package 'playwright' is not installed. "
                "Install it and the browser runtime before running browser smoke tests."
            ) from exc

        self._playwright = sync_playwright().start()
        launch_kwargs: dict[str, Any] = {"headless": self.headless}
        executable_path = _find_downloaded_chromium()
        if executable_path is not None:
            launch_kwargs["executable_path"] = str(executable_path)
        self._browser = self._playwright.chromium.launch(**launch_kwargs)
        self._context = self._browser.new_context(accept_downloads=True)
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.timeout_ms)

    def close(self) -> None:
        """Close page, browser, and Playwright runtime if they were started."""

        if self._page is not None:
            self._page.close()
            self._page = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._context is not None:
            self._context = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    @property
    def page(self) -> Any:
        if self._page is None:
            raise MissingBrowserDependency("Playwright executor has not been started")
        return self._page

    def open(self, url_or_path: str | Path) -> BrowserObservation:
        """Navigate to a URL or local file path and return an observation."""

        target = str(url_or_path)
        if not target.startswith(("http://", "https://", "file://")):
            target = Path(target).resolve().as_uri()
        self.page.goto(target)
        return self.observe_page()

    def observe_page(self) -> BrowserObservation:
        """Return a compact page snapshot."""

        page = self.page
        elements = page.locator("a, button, input, select, textarea").evaluate_all(
            r"""els => {
                const cssEscape = value => {
                    if (window.CSS && window.CSS.escape) {
                        return window.CSS.escape(value);
                    }
                    return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
                };
                const quoteAttr = value => String(value)
                    .replace(/\\/g, "\\\\")
                    .replace(/"/g, "\\\"");
                const sameTagIndex = el => Array.from(
                    document.querySelectorAll(el.tagName.toLowerCase())
                ).indexOf(el);
                const countFor = selector => {
                    try {
                        return document.querySelectorAll(selector).length;
                    } catch (error) {
                        return 0;
                    }
                };
                const nthFor = (selector, el) => {
                    try {
                        return Array.from(document.querySelectorAll(selector)).indexOf(el);
                    } catch (error) {
                        return -1;
                    }
                };
                const uniqueOrNth = (selector, strategy, el) => {
                    const count = countFor(selector);
                    if (count === 1) {
                        return {selector, selector_strategy: strategy, selector_unique: true};
                    }
                    const nth = nthFor(selector, el);
                    if (nth >= 0) {
                        return {
                            selector: `${selector} >> nth=${nth}`,
                            selector_strategy: `${strategy}_nth`,
                            selector_unique: true,
                        };
                    }
                    return null;
                };
                const selectorFor = el => {
                    const tag = el.tagName.toLowerCase();
                    const testId = el.getAttribute("data-testid");
                    if (testId) {
                        const candidate = uniqueOrNth(`[data-testid="${quoteAttr(testId)}"]`, "data-testid", el);
                        if (candidate) return candidate;
                    }
                    if (el.id) {
                        const candidate = uniqueOrNth(`#${cssEscape(el.id)}`, "id", el);
                        if (candidate) return candidate;
                    }
                    const name = el.getAttribute("name");
                    if (name) {
                        const candidate = uniqueOrNth(`${tag}[name="${quoteAttr(name)}"]`, "name", el);
                        if (candidate) return candidate;
                    }
                    return {
                        selector: `${tag} >> nth=${sameTagIndex(el)}`,
                        selector_strategy: "tag_nth",
                        selector_unique: true,
                    };
                };
                return els.slice(0, 50).map((el, index) => ({
                    index,
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim(),
                    value: 'value' in el ? el.value : undefined,
                    options: el.tagName.toLowerCase() === 'select'
                        ? Array.from(el.options).map(option => option.value || option.textContent.trim())
                        : undefined,
                    download: el.getAttribute('download'),
                    href: el.getAttribute('href'),
                    name: el.getAttribute('name'),
                    id: el.id,
                    testid: el.getAttribute('data-testid'),
                    type: el.getAttribute('type'),
                    checked: typeof el.checked === 'boolean' ? el.checked : undefined,
                    role: el.getAttribute('role'),
                    aria_label: el.getAttribute('aria-label'),
                    ...selectorFor(el),
                }));
            }"""
        )
        return BrowserObservation(
            url=page.url,
            title=page.title(),
            text=page.locator("body").inner_text(timeout=self.timeout_ms),
            elements=elements,
        )

    def execute(self, action: BrowserAction) -> BrowserActionResult:
        """Validate and execute one browser action."""

        try:
            action.validate()
            if action.name == "observe_page":
                return BrowserActionResult(action=action, ok=True, observation=self.observe_page())
            if action.name == "click":
                self.page.locator(action.selector).click()
                return BrowserActionResult(action=action, ok=True, observation=self.observe_page())
            if action.name == "type":
                self.page.locator(action.selector).fill(action.text or "")
                return BrowserActionResult(action=action, ok=True, observation=self.observe_page())
            if action.name == "select":
                self.page.locator(action.selector).select_option(action.value)
                return BrowserActionResult(action=action, ok=True, observation=self.observe_page())
            if action.name == "extract_text":
                extracted = self.page.locator(action.selector).inner_text()
                return BrowserActionResult(
                    action=action,
                    ok=True,
                    observation=self.observe_page(),
                    extracted_text=extracted,
                )
            if action.name == "download_file":
                with self.page.expect_download() as download_info:
                    self.page.locator(action.selector).click()
                download = download_info.value
                download_dir = Path("artifacts") / "downloads"
                download_dir.mkdir(parents=True, exist_ok=True)
                download_path = download_dir / download.suggested_filename
                download.save_as(download_path)
                return BrowserActionResult(
                    action=action,
                    ok=True,
                    observation=self.observe_page(),
                    download_path=str(download_path),
                )
            if action.name == "finish":
                return BrowserActionResult(action=action, ok=True, observation=self.observe_page())
        except Exception as exc:  # Playwright raises several runtime-specific exception classes.
            error = str(exc)
            return BrowserActionResult.failure(action, error, error_type=_classify_error(error))
        return BrowserActionResult.failure(
            action,
            f"Unsupported action: {action.name}",
            error_type="unsupported_action",
        )


def _classify_error(error: str) -> str:
    """Map Playwright/runtime messages to stable trace error types."""

    normalized = re.sub(r"\s+", " ", error.lower())
    if "strict mode violation" in normalized:
        return "strict_mode_violation"
    if "unsupported action" in normalized or "not implemented" in normalized:
        return "unsupported_action"
    if "waiting for locator" in normalized and "resolved to 0 elements" in normalized:
        return "element_not_found"
    if "locator" in normalized and "not found" in normalized:
        return "element_not_found"
    if "timeout" in normalized:
        return "timeout"
    return "browser_error"


def _find_downloaded_chromium() -> Path | None:
    """Return a downloaded full Chromium executable if Playwright has one.

    Playwright 1.60 prefers the headless shell for headless launches. On this
    Windows setup the full Chromium artifact may be present while the headless
    shell download is incomplete, so we explicitly point to full Chrome when it
    exists.
    """

    roots = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        roots.append(Path(local_app_data) / "ms-playwright")
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path:
        roots.append(Path(browsers_path))

    for root in roots:
        if not root.exists():
            continue
        for candidate in sorted(root.glob("chromium-*/chrome-win64/chrome.exe"), reverse=True):
            if candidate.exists():
                return candidate
    return None
