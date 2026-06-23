import unittest

from src.llm.adapters import LLMRequest, _format_prompt


class LLMAdapterTests(unittest.TestCase):
    def test_ollama_prompt_uses_compact_action_contract(self):
        prompt = _format_prompt(
            LLMRequest(
                task="Select Northstar Clinics.",
                observation='Elements:\n- selector: [data-testid="select-northstar-clinics"]; text: Select',
                action_schema={
                    "properties": {
                        "metadata": {
                            "description": "This verbose schema should not be inlined into the prompt."
                        }
                    }
                },
                safety_policy="Use conservative defaults.",
            )
        )

        self.assertLess(len(prompt), 2000)
        self.assertIn("Return a compact object", prompt)
        self.assertIn("tag: select", prompt)
        self.assertNotIn("verbose schema should not be inlined", prompt)


if __name__ == "__main__":
    unittest.main()
