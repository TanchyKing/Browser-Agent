import unittest

from finetune.export_mock_traces import FAILED_PHASE1_BUSINESS
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
    def test_valid_sample_passes_dependency_free_validator(self):
        self.assertEqual(validate_sample(sample()), [])

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


if __name__ == "__main__":
    unittest.main()
