import unittest

from finetune.export_mock_traces import FAILED_PHASE1_BUSINESS
from finetune.apply_review_queue import apply_decisions
from finetune.split_dataset import split_samples
from finetune.validate_dataset import validate_sample


def sample(template="family"):
    return {
        "sample_id": "a" * 64,
        "family": template,
        "template_id": template,
        "split": "unassigned",
        "review_status": "draft",
        "source_task_id": "visible_task",
        "task_contract": "Do visible task",
        "observation": "- selector: #safe",
        "agent_state": None,
        "tools_schema": {},
        "candidate_snapshot": {"selectors": ["#safe"]},
        "completion": {"action": "click", "target": "#safe", "value": None, "reason": "click safe", "risk_level": "low", "metadata": {}},
        "tool_result": {"ok": True},
        "safety_labels": [],
        "correction_for": None,
        "provenance": {"run_id": "run", "step_index": 0, "config_sha256": None, "source_artifact": "artifact"},
    }


class DataPipelineTests(unittest.TestCase):
    def test_valid_sample_passes_grounding_validator(self):
        self.assertEqual(validate_sample(sample()), [])

    def test_ungrounded_completion_target_is_rejected(self):
        item = sample()
        item["completion"]["target"] = "#not-observed"

        self.assertIn(
            "completion target is not grounded in candidate_snapshot",
            validate_sample(item),
        )

    def test_equivalent_selector_quote_style_is_grounded(self):
        item = sample()
        item["candidate_snapshot"] = {"selectors": ['[data-testid="safe"]']}
        item["completion"]["target"] = "[data-testid='safe']"

        self.assertEqual(validate_sample(item), [])

    def test_heldout_source_is_rejected(self):
        item = sample()
        item["source_task_id"] = "heldout_jobs_secret"

        self.assertIn("held-out or blind data reference is forbidden", validate_sample(item))

    def test_template_group_never_crosses_splits(self):
        rows = [sample("jobs"), sample("jobs"), sample("invoice")]
        split_samples(rows)

        self.assertEqual(rows[0]["split"], rows[1]["split"])

    def test_phase1_failure_correction_set_has_six_business_tasks(self):
        self.assertEqual(len(FAILED_PHASE1_BUSINESS), 6)

    def test_review_queue_only_marks_explicit_approval_reviewed(self):
        approved = sample("approved")
        pending = sample("pending")
        pending["sample_id"] = "b" * 64
        output = apply_decisions(
            [approved, pending],
            {
                approved["sample_id"]: {"decision": "approve"},
                pending["sample_id"]: {"decision": "modify"},
            },
        )

        self.assertEqual(output[0]["review_status"], "reviewed")
        self.assertEqual(output[1]["review_status"], "draft")


if __name__ == "__main__":
    unittest.main()
