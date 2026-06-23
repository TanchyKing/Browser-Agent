import unittest

from src.eval.error_analysis import analyze_errors, classify_error_type, collect_error_events, render_trace_replay


class ErrorAnalysisTest(unittest.TestCase):
    def test_collects_step_and_run_level_errors(self):
        run = {
            "task_id": "task",
            "run_id": "run",
            "status": "failed",
            "steps": [{"step_index": 2, "action_type": "click", "error_type": "element_target_error"}],
            "errors": [{"type": "premature_finish", "message": "finished early"}],
        }

        events = collect_error_events(run)

        self.assertEqual([event["type"] for event in events], ["element_target_error", "premature_finish"])

    def test_analyzes_error_counts_and_failed_runs(self):
        analysis = analyze_errors(
            [
                {"task_id": "ok", "run_id": "1", "status": "success", "steps": []},
                {
                    "task_id": "bad",
                    "run_id": "2",
                    "status": "failed",
                    "steps": [{"error_type": "wrong_action"}],
                },
            ]
        )

        self.assertEqual(analysis["error_counts"], {"wrong_action": 1})
        self.assertEqual(len(analysis["failed_runs"]), 1)
        self.assertIn("wrong_action", analysis["taxonomy"])

    def test_renders_markdown_trace_replay(self):
        replay = render_trace_replay(
            {
                "task_id": "task",
                "run_id": "run",
                "status": "failed",
                "duration_ms": 10,
                "steps": [
                    {
                        "step_index": 1,
                        "action_type": "click",
                        "valid_action": False,
                        "error_type": "wrong_action",
                    }
                ],
            }
        )

        self.assertIn("Trace Replay", replay)
        self.assertIn("wrong_action", replay)
        self.assertIn("INVALID", replay)

    def test_classifies_browser_execution_errors(self):
        self.assertEqual(
            classify_error_type('Locator.click: Error: strict mode violation: resolved to 3 elements'),
            "strict_mode_multiple_matches",
        )
        self.assertEqual(classify_error_type("Timeout 30000ms exceeded"), "timeout")
        self.assertEqual(classify_error_type("element not found for #submit"), "element_not_found")
        self.assertEqual(classify_error_type("unsupported browser action: hover"), "unsupported_action")


if __name__ == "__main__":
    unittest.main()
