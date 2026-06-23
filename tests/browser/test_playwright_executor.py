import importlib.util
import unittest

from src.browser import MissingBrowserDependency
from src.browser.playwright_executor import PlaywrightBrowserExecutor


class PlaywrightExecutorDependencyTest(unittest.TestCase):
    def test_missing_playwright_is_explicit(self) -> None:
        if importlib.util.find_spec("playwright") is not None:
            self.skipTest("playwright is installed in this environment")
        executor = PlaywrightBrowserExecutor()
        with self.assertRaises(MissingBrowserDependency):
            executor.start()


if __name__ == "__main__":
    unittest.main()
