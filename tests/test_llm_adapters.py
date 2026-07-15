import unittest

from src.llm.adapters import LLMRequest, OllamaAdapter, _format_prompt


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

    def test_legacy_ollama_body_preserves_phase1_defaults(self):
        adapter = OllamaAdapter()
        body = adapter.request_body(LLMRequest(task="task", observation="page"), prompt="prompt")

        self.assertEqual(body["format"], "json")
        self.assertEqual(body["options"], {"temperature": 0.0, "num_predict": 768})
        self.assertNotIn("think", body)

    def test_schema_and_think_are_explicit_ablation_switches(self):
        schema = {"type": "object", "properties": {"action": {"type": "string"}}}
        adapter = OllamaAdapter(think=False, format_mode="schema", num_predict=256)
        body = adapter.request_body(
            LLMRequest(task="task", observation="page", action_schema=schema),
            prompt="prompt",
        )

        self.assertIs(body["format"], schema)
        self.assertFalse(body["think"])
        self.assertEqual(body["options"]["num_predict"], 256)

    def test_v2_prompt_removes_copyable_finish_template(self):
        request = LLMRequest(task="Summarize the safe brief.", observation="page")

        legacy = _format_prompt(request)
        revised = _format_prompt(request, action_template_version="v2")

        self.assertIn("visible confirmation proves completion", legacy)
        self.assertNotIn("visible confirmation proves completion", revised)
        self.assertIn("extract_text from the element containing the safe brief", revised)
        self.assertNotIn('"action":"finish"', revised)

    def test_v2_terminal_answer_prompt_separates_reason_from_answer(self):
        prompt = _format_prompt(
            LLMRequest(task="Summarize.", observation="page"),
            action_template_version="v2",
            terminal_answer_enabled=True,
        )

        self.assertIn("metadata, answer", prompt)
        self.assertIn("answer as a separate user-facing field", prompt)
        self.assertIn("reason explains only why the action is next", prompt)


if __name__ == "__main__":
    unittest.main()
