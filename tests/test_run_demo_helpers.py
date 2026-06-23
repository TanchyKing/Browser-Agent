import unittest

from scripts.run_demo import _selector_for_element, collect_final_state, format_task_prompt


class RunDemoHelperTests(unittest.TestCase):
    def test_selector_for_element_prefers_executor_selector(self):
        selector = _selector_for_element(
            {
                "selector": "[data-testid='select-northstar-clinics']",
                "id": "fallback",
                "text": "Select",
                "tag": "button",
            }
        )

        self.assertEqual(selector, "[data-testid='select-northstar-clinics']")

    def test_format_task_prompt_includes_element_text_completion_criteria(self):
        prompt = format_task_prompt(
            {
                "instruction": "Select Northstar Clinics.",
                "success_check": {
                    "all_of": [
                        {
                            "kind": "element_text",
                            "target": "[data-testid='selected-customer']",
                            "value": "Northstar Clinics",
                        }
                    ]
                },
            }
        )

        self.assertIn("Completion criteria:", prompt)
        self.assertIn("[data-testid='selected-customer']", prompt)
        self.assertIn("return finish", prompt)

    def test_collect_final_state_returns_element_text_evidence(self):
        class FakeExecutor:
            class Page:
                class Locator:
                    def count(self):
                        return 1

                    @property
                    def first(self):
                        return self

                    def inner_text(self):
                        return "Northstar Clinics"

                def locator(self, selector):
                    return self.Locator()

            page = Page()

        final_state = collect_final_state(
            FakeExecutor(),
            {
                "success_check": {
                    "all_of": [
                        {
                            "kind": "element_text",
                            "target": "[data-testid='selected-customer']",
                            "value": "Northstar Clinics",
                        }
                    ]
                }
            },
        )

        self.assertEqual(
            final_state["elements"]["[data-testid='selected-customer']"]["text"],
            "Northstar Clinics",
        )


if __name__ == "__main__":
    unittest.main()
