import unittest

from finetune.export_mock_traces import FAILED_PHASE1_BUSINESS
from finetune.apply_review_queue import apply_decisions
from finetune.split_dataset import split_samples
from finetune.validate_dataset import validate_sample
from finetune.interface_rendering import render_sample
from finetune.prepare_sft import prepare_records


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
        "semantic_completion": {"action_reason": "click safe", "user_visible_result": None},
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

    def test_terminal_semantics_render_to_r10e_and_r10f_without_second_label(self):
        item = sample()
        item["completion"] = {
            "action": "finish",
            "target": None,
            "value": None,
            "reason": "14 active records remain unchanged.",
            "risk_level": "low",
            "metadata": {},
        }
        item["semantic_completion"] = {
            "action_reason": "Return the observed result.",
            "user_visible_result": "14 active records remain unchanged.",
        }
        item["tools_schema"] = {
            "type": "object",
            "required": ["action", "reason"],
            "properties": {
                "action": {"const": "finish"},
                "reason": {"type": "string"},
                "target": {"type": ["string", "null"]},
                "value": {},
                "risk_level": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "additionalProperties": False,
        }

        r10e = render_sample(item, "r10e")
        r10f = render_sample(item, "r10f")

        self.assertNotIn("answer", r10e["completion"])
        self.assertEqual(r10e["completion"]["reason"], item["semantic_completion"]["user_visible_result"])
        self.assertEqual(r10f["completion"]["reason"], "Return the observed result.")
        self.assertEqual(r10f["completion"]["answer"], item["semantic_completion"]["user_visible_result"])
        self.assertIn("answer", r10f["tools_schema"]["properties"])

    def test_terminal_semantics_must_match_canonical_r10e_reason(self):
        item = sample()
        item["completion"].update({"action": "finish", "target": None, "reason": "generic"})
        item["semantic_completion"] = {
            "action_reason": "Return the observed result.",
            "user_visible_result": "specific fact",
        }

        self.assertIn(
            "canonical R10e terminal reason must equal semantic user_visible_result",
            validate_sample(item),
        )

    def test_prepare_sft_renders_both_interfaces_from_one_reviewed_sample(self):
        item = sample()
        item["review_status"] = "reviewed"
        item["completion"] = {
            "action": "finish",
            "target": None,
            "value": None,
            "reason": "14 active records remain unchanged.",
            "risk_level": "low",
            "metadata": {},
        }
        item["semantic_completion"] = {
            "action_reason": "Return the observed result.",
            "user_visible_result": "14 active records remain unchanged.",
        }
        item["tools_schema"] = {
            "type": "object",
            "required": ["action", "reason"],
            "properties": {
                "action": {"const": "finish"},
                "reason": {"type": "string"},
                "target": {"type": ["string", "null"]},
                "value": {},
                "risk_level": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "additionalProperties": False,
        }

        r10e = prepare_records([item], interface="r10e")
        r10f = prepare_records([item], interface="r10f")

        self.assertEqual(r10e[0]["interface"], "r10e")
        self.assertNotIn('"answer"', r10e[0]["text"].split("Assistant action:\n", 1)[1])
        self.assertEqual(r10f[0]["interface"], "r10f")
        self.assertIn('"answer":"14 active records remain unchanged."', r10f[0]["text"])


if __name__ == "__main__":
    unittest.main()
