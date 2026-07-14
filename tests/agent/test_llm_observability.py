import unittest

from src.agent.runner import BrowserAgentRunner
from src.llm import LLMResponse


class _StaticTools:
    def observe_page(self):
        return "Contact admin@example.com and use token=page-secret"

    def execute(self, action):
        return {"ok": True}


class _TruncatedAdapter:
    model_name = "audit-model"

    def complete(self, request):
        return LLMResponse(
            content='{"action":"finish","reason":"token=response-secret',
            model=self.model_name,
            raw={
                "done": True,
                "done_reason": "length",
                "eval_count": 768,
                "prompt_eval_count": 100,
            },
        )


class LLMObservabilityTests(unittest.TestCase):
    def test_invalid_response_records_redacted_audit_and_truncation(self):
        result = BrowserAgentRunner(
            _TruncatedAdapter(),
            _StaticTools(),
            max_json_retries=0,
            action_schema={"type": "object"},
        ).run("Email admin@example.com with token=task-secret")

        self.assertFalse(result.completed)
        audit = result.steps[0].result["llm_attempts"][0]
        self.assertFalse(audit["parse_valid"])
        self.assertEqual(audit["response"]["done_reason"], "length")
        self.assertTrue(audit["response"]["truncated"])
        self.assertIsInstance(audit["parse_error_position"], int)
        self.assertIn("<redacted-email>", audit["request"]["task_preview"])
        self.assertNotIn("task-secret", audit["request"]["task_preview"])
        self.assertNotIn("response-secret", audit["response"]["raw_response_preview"])
        self.assertEqual(audit["response"]["eval_count"], 768)

    def test_bounded_retry_omits_page_prose_but_keeps_grounded_selectors(self):
        class CaptureAdapter:
            model_name = "capture"

            def __init__(self):
                self.requests = []

            def complete(self, request):
                self.requests.append(request)
                if len(self.requests) == 1:
                    return LLMResponse('{"action":"click"', model=self.model_name)
                return LLMResponse(
                    '{"action":"finish","reason":"valid retry","risk_level":"low"}',
                    model=self.model_name,
                )

        adapter = CaptureAdapter()

        class SelectorTools(_StaticTools):
            def observe_page(self):
                return "- selector: #safe; tag: button; text: Safe\nVisible text:\nDO NOT COPY THIS PROSE"

        result = BrowserAgentRunner(
            adapter,
            SelectorTools(),
            max_json_retries=1,
            retry_prompt_mode="bounded",
        ).run("Click the safe control. " + "long task " * 100)

        self.assertTrue(result.completed)
        self.assertEqual(len(adapter.requests), 2)
        self.assertIn("#safe", adapter.requests[1].observation)
        self.assertNotIn("DO NOT COPY THIS PROSE", adapter.requests[1].observation)
        self.assertLessEqual(len(adapter.requests[1].task), 500)


if __name__ == "__main__":
    unittest.main()
