import tempfile
import unittest
from pathlib import Path

from dashboard.render_report import render_html, render_report


class DashboardReportTest(unittest.TestCase):
    def test_render_html_contains_summary_errors_and_failed_runs(self):
        html = render_html(
            {
                "source": "mock.json",
                "summary": {"total_runs": 2, "task_success_rate": 0.5, "error_counts": {}},
                "run_groups": {"source_kind": {"scripted_safety": 1}, "llm_backend": {"none": 1}},
                "success_checks": {"annotated_runs": 1, "unsupported_runs": 0},
                "error_analysis": {
                    "error_counts": {"wrong_action": 1},
                    "failed_runs": [
                        {
                            "task_id": "task",
                            "run_id": "run",
                            "status": "failed",
                            "error_events": [{"type": "wrong_action"}],
                        }
                    ],
                },
            }
        )

        self.assertIn("Browser Agent Evaluation Report", html)
        self.assertIn("task_success_rate", html)
        self.assertIn("wrong_action", html)
        self.assertIn("policy-unit checks", html)

    def test_render_report_writes_html_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"
            out_html = Path(tmpdir) / "report.html"
            summary_path.write_text(
                '{"source":"mock","summary":{"total_runs":0},"error_analysis":{"error_counts":{},"failed_runs":[]}}',
                encoding="utf-8",
            )

            render_report(summary_path, out_html)

            self.assertTrue(out_html.exists())
            self.assertIn("total_runs", out_html.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
