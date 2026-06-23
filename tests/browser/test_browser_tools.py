import unittest

from src.browser import BrowserAction, BrowserToolError


class BrowserActionValidationTest(unittest.TestCase):
    def test_click_requires_selector(self) -> None:
        with self.assertRaises(BrowserToolError):
            BrowserAction(name="click").validate()

    def test_type_requires_text(self) -> None:
        with self.assertRaises(BrowserToolError):
            BrowserAction(name="type", selector="#name").validate()

    def test_finish_requires_reason(self) -> None:
        with self.assertRaises(BrowserToolError):
            BrowserAction(name="finish").validate()

    def test_valid_type_action(self) -> None:
        BrowserAction(name="type", selector="#name", text="Alice").validate()


if __name__ == "__main__":
    unittest.main()
