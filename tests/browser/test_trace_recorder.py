import tempfile
import unittest
from pathlib import Path

from src.browser import BrowserAction, BrowserActionResult, BrowserObservation
from src.tracing import TraceRecorder


class TraceRecorderTest(unittest.TestCase):
    def test_record_result_writes_jsonl_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "trace.jsonl"
            recorder = TraceRecorder(output_path, run_id="run-test")
            action = BrowserAction(name="observe_page")
            observation = BrowserObservation(
                url="file:///task.html",
                title="Task",
                text="Hello" * 300,
                elements=[
                    {
                        "tag": "button",
                        "text": "Submit",
                        "selector": "[data-testid=\"submit\"]",
                        "selector_strategy": "data-testid",
                    }
                ],
            )
            result = BrowserActionResult(action=action, ok=True, observation=observation)

            step = recorder.record_result(result, elapsed_ms=12, metadata={"task_id": "t1"})
            rows = recorder.read_steps()

            self.assertEqual(step.step_index, 0)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["run_id"], "run-test")
            self.assertEqual(rows[0]["step_index"], 0)
            self.assertEqual(rows[0]["action"]["name"], "observe_page")
            self.assertEqual(rows[0]["observation"]["title"], "Task")
            self.assertIn("text_excerpt", rows[0]["observation"])
            self.assertEqual(rows[0]["observation"]["elements"][0]["selector"], "[data-testid=\"submit\"]")
            self.assertEqual(rows[0]["metadata"]["task_id"], "t1")

    def test_record_result_writes_error_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "trace.jsonl"
            recorder = TraceRecorder(output_path, run_id="run-test")
            action = BrowserAction(name="click", selector="button")
            result = BrowserActionResult.failure(
                action,
                "strict mode violation",
                error_type="strict_mode_violation",
            )

            recorder.record_result(result, elapsed_ms=7)
            rows = recorder.read_steps()

            self.assertFalse(rows[0]["ok"])
            self.assertEqual(rows[0]["error_type"], "strict_mode_violation")
            self.assertEqual(rows[0]["elapsed_ms"], 7)


if __name__ == "__main__":
    unittest.main()
