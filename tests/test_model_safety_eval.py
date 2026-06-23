import unittest

from scripts.run_model_safety_eval import DEFAULT_SAFETY_TASKS, _forbidden_selectors, _unsafe_step


class ModelSafetyEvalTests(unittest.TestCase):
    def test_default_safety_tasks_include_variants(self):
        self.assertGreaterEqual(len(DEFAULT_SAFETY_TASKS), 7)
        self.assertIn("resist_prompt_injection_payment", DEFAULT_SAFETY_TASKS)
        self.assertIn("resist_prompt_injection_credentials", DEFAULT_SAFETY_TASKS)

    def test_forbidden_selectors_are_loaded_from_task_file(self):
        selectors = _forbidden_selectors(["resist_prompt_injection_payment"])

        self.assertIn("[data-testid='submit-payment']", selectors["resist_prompt_injection_payment"])

    def test_unsafe_step_uses_task_specific_forbidden_selectors(self):
        unsafe = _unsafe_step(
            {
                "task_id": "resist_prompt_injection_payment",
                "steps": [
                    {
                        "action_type": "click",
                        "target": "[data-testid='submit-payment']",
                        "execution_ok": True,
                        "safety_violation": False,
                    }
                ],
            },
            {"resist_prompt_injection_payment": {"[data-testid='submit-payment']"}},
        )

        self.assertIsNotNone(unsafe)


if __name__ == "__main__":
    unittest.main()
