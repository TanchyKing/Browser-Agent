import importlib.util
import tempfile
import unittest
from pathlib import Path

from src.browser import BrowserAction
from src.browser.playwright_executor import PlaywrightBrowserExecutor


FIXTURE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Selector Fixture</title>
</head>
<body>
  <button data-testid="save-action">Save</button>
  <input id="customer-name" />
  <input id="approval" type="checkbox" checked />
  <select name="plan"><option value="basic">Basic</option></select>
  <p data-testid="safe-brief">Safe brief: three records remain unchanged.</p>
  <button onclick="document.getElementById('status').innerText='first'">Select</button>
  <button onclick="document.getElementById('status').innerText='second'">Select</button>
  <p id="status">none</p>
</body>
</html>
"""


def playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


@unittest.skipUnless(playwright_available(), "playwright is not installed")
class PlaywrightObservationTest(unittest.TestCase):
    def test_observation_exposes_stable_executable_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "selector_fixture.html"
            fixture.write_text(FIXTURE_HTML, encoding="utf-8")

            with PlaywrightBrowserExecutor(
                headless=True,
                timeout_ms=5000,
                include_readonly_testid_nodes=True,
            ) as executor:
                observation = executor.open(fixture)

                save = next(element for element in observation.elements if element.get("testid") == "save-action")
                customer = next(element for element in observation.elements if element.get("id") == "customer-name")
                approval = next(element for element in observation.elements if element.get("id") == "approval")
                plan = next(element for element in observation.elements if element.get("name") == "plan")
                brief = next(element for element in observation.elements if element.get("testid") == "safe-brief")
                self.assertEqual(save["selector"], '[data-testid="save-action"]')
                self.assertEqual(customer["selector"], "#customer-name")
                self.assertEqual(approval["type"], "checkbox")
                self.assertTrue(approval["checked"])
                self.assertEqual(plan["selector"], 'select[name="plan"]')
                self.assertEqual(plan["value"], "basic")
                self.assertEqual(brief["selector"], '[data-testid="safe-brief"]')
                self.assertEqual(brief["tag"], "p")
                self.assertIn("three records remain unchanged", brief["text"])
                select_buttons = [element for element in observation.elements if element.get("text") == "Select"]
                self.assertEqual([element["selector"] for element in select_buttons], ["button >> nth=1", "button >> nth=2"])

                result = executor.execute(BrowserAction(name="click", selector=select_buttons[1]["selector"]))

            self.assertTrue(result.ok, result.error)
            self.assertIn("second", result.observation.text)

    def test_interactive_only_mode_excludes_readonly_testid_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "selector_fixture.html"
            fixture.write_text(FIXTURE_HTML, encoding="utf-8")

            with PlaywrightBrowserExecutor(
                headless=True,
                timeout_ms=5000,
                include_readonly_testid_nodes=False,
            ) as executor:
                observation = executor.open(fixture)

            testids = {element.get("testid") for element in observation.elements}
            self.assertIn("save-action", testids)
            self.assertNotIn("safe-brief", testids)

    def test_strict_mode_violation_is_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "selector_fixture.html"
            fixture.write_text(FIXTURE_HTML, encoding="utf-8")

            with PlaywrightBrowserExecutor(headless=True, timeout_ms=3000) as executor:
                executor.open(fixture)
                result = executor.execute(BrowserAction(name="click", selector="button:has-text('Select')"))

            self.assertFalse(result.ok)
            self.assertEqual(result.error_type, "strict_mode_violation")
            self.assertIn("strict mode violation", result.error)


if __name__ == "__main__":
    unittest.main()
