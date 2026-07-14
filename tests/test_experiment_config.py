import json
import tempfile
import unittest
from pathlib import Path

from src.experiment_config import (
    ExperimentConfig,
    load_experiment_config,
    load_suite_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class ExperimentConfigTests(unittest.TestCase):
    def test_checked_in_r1_config_matches_phase1_inference_defaults(self):
        config = load_experiment_config(ROOT / "configs" / "phase2" / "r1_legacy.yaml")

        self.assertEqual(config.inference.model_name, "qwen3:8b")
        self.assertIsNone(config.inference.think)
        self.assertEqual(config.inference.format_mode, "json")
        self.assertEqual(config.inference.num_predict, 768)
        self.assertEqual(config.runner.max_steps, 8)

    def test_digest_does_not_depend_on_config_source_path(self):
        config = ExperimentConfig()
        loaded = load_experiment_config(ROOT / "configs" / "phase2" / "r1_legacy.yaml")

        self.assertEqual(config.digest(), loaded.digest())

    def test_frozen_phase1_manifests_have_expected_cardinality(self):
        business = load_suite_manifest(ROOT / "configs" / "suites" / "phase1_qwen12.json")
        safety = load_suite_manifest(ROOT / "configs" / "suites" / "phase1_safety7.json")

        self.assertEqual(len(business.task_ids), 12)
        self.assertEqual(len(safety.task_ids), 7)
        self.assertIn("extract_q2_report_name", business.task_ids)
        self.assertIn("resist_prompt_injection_credentials", safety.task_ids)

    def test_manifest_rejects_duplicate_task_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text(
                json.dumps({"suite_id": "bad", "task_ids": ["one", "one"]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_suite_manifest(path)

    def test_r2_switches_grader_and_prompt_without_changing_inference_defaults(self):
        config = load_experiment_config(ROOT / "configs" / "phase2" / "r2_fixed_grader.yaml")

        self.assertEqual(config.evaluator.grader_version, "v2")
        self.assertEqual(config.prompt.mode, "contract")
        self.assertEqual(config.inference.model_name, "qwen3:8b")
        self.assertEqual(config.inference.format_mode, "json")

    def test_ablation_config_inherits_parent_and_changes_only_declared_fields(self):
        r3 = load_experiment_config(ROOT / "configs" / "phase2" / "r3_think_false.yaml")
        r4 = load_experiment_config(ROOT / "configs" / "phase2" / "r4_bounded_schema.yaml")

        self.assertFalse(r3.inference.think)
        self.assertEqual(r3.inference.format_mode, "json")
        self.assertEqual(r3.evaluator.grader_version, "v2")
        self.assertFalse(r4.inference.think)
        self.assertEqual(r4.inference.format_mode, "schema")
        self.assertTrue(r4.inference.structured_validation)
        self.assertEqual(r4.inference.num_predict, 768)


if __name__ == "__main__":
    unittest.main()
