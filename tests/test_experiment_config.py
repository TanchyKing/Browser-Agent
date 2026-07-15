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

    def test_post_audit_configs_restore_thinking_then_isolate_trust_and_model(self):
        r10b = load_experiment_config(ROOT / "configs" / "phase2" / "r10b_think_true.yaml")
        r10c = load_experiment_config(
            ROOT / "configs" / "phase2" / "r10c_trust_partition.yaml"
        )
        r11b = load_experiment_config(
            ROOT / "configs" / "phase2" / "r11b_qwen3_14b_fair.yaml"
        )

        self.assertTrue(r10b.inference.think)
        self.assertFalse(r10b.controller.trust_partition_enabled)
        self.assertTrue(r10b.controller.block_recovery_enabled)
        self.assertTrue(r10c.inference.think)
        self.assertTrue(r10c.controller.trust_partition_enabled)
        self.assertEqual(r10c.inference.model_name, "qwen3:8b")
        self.assertTrue(r11b.inference.think)
        self.assertTrue(r11b.controller.trust_partition_enabled)
        self.assertEqual(r11b.inference.model_name, "qwen3:14b")

    def test_post_audit_engineering_configs_change_one_layer_at_a_time(self):
        r10c = load_experiment_config(ROOT / "configs" / "phase2" / "r10c_trust_partition.yaml")
        r10d = load_experiment_config(ROOT / "configs" / "phase2" / "r10d_contract_fixes.yaml")
        r10e = load_experiment_config(ROOT / "configs" / "phase2" / "r10e_prompt_v2.yaml")
        r10f = load_experiment_config(ROOT / "configs" / "phase2" / "r10f_terminal_answer.yaml")
        r10g = load_experiment_config(ROOT / "configs" / "phase2" / "r10g_observation_fix.yaml")

        self.assertIsNone(r10c.prompt.agent_contract_overrides_path)
        self.assertEqual(r10d.prompt.agent_contract_overrides_path, "tasks/phase2_agent_contract_v2.json")
        self.assertEqual(r10d.prompt.action_template_version, "v1")
        self.assertEqual(r10e.prompt.action_template_version, "v2")
        self.assertFalse(r10e.inference.terminal_answer_enabled)
        self.assertTrue(r10f.inference.terminal_answer_enabled)
        self.assertEqual(
            r10f.inference.action_schema_path,
            "configs/schema/action.terminal-answer.schema.json",
        )
        self.assertEqual(r10f.inference.model_name, "qwen3:8b")
        self.assertTrue(r10f.inference.think)
        self.assertTrue(r10f.controller.trust_partition_enabled)
        self.assertEqual(r10e.browser.observation_mode, "interactive_only")
        self.assertEqual(r10f.browser.observation_mode, "interactive_only")
        self.assertEqual(r10g.browser.observation_mode, "visible_testids")
        r10e_values = r10e.values()
        r10g_values = r10g.values()
        r10e_values["experiment_id"] = r10g_values["experiment_id"]
        r10g_values.pop("browser")
        self.assertEqual(r10e_values, r10g_values)
        self.assertEqual(
            r10c.digest().upper(),
            "AB8BC302B27E04985D078AB0F884F7D699859EC1A6347A5C96EFF95A07AFE1A0",
        )

    def test_r10b_and_r10c_heldout_overlays_preserve_controller_difference(self):
        r10b = load_experiment_config(ROOT / "configs" / "phase2" / "r10b_think_true_heldout.yaml")
        r10c = load_experiment_config(ROOT / "configs" / "phase2" / "r10c_trust_partition_heldout.yaml")

        self.assertEqual(r10b.evaluator.task_file_path, "tasks/development_heldout_tasks.jsonl")
        self.assertEqual(r10c.evaluator.task_file_path, "tasks/development_heldout_tasks.jsonl")
        self.assertEqual(
            r10b.prompt.agent_contract_overrides_path,
            "tasks/phase2_development_agent_contract_v2.json",
        )
        self.assertEqual(
            r10c.prompt.agent_contract_overrides_path,
            "tasks/phase2_development_agent_contract_v2.json",
        )
        self.assertFalse(r10b.controller.trust_partition_enabled)
        self.assertTrue(r10c.controller.trust_partition_enabled)
        self.assertTrue(r10b.inference.think)
        self.assertTrue(r10c.inference.think)

    def test_r10g_heldout_preserves_observation_fix_and_uses_public_contract(self):
        heldout = load_experiment_config(
            ROOT / "configs" / "phase2" / "r10g_observation_fix_heldout.yaml"
        )

        self.assertEqual(heldout.browser.observation_mode, "visible_testids")
        self.assertEqual(heldout.evaluator.task_file_path, "tasks/development_heldout_tasks.jsonl")
        self.assertEqual(
            heldout.prompt.agent_contract_overrides_path,
            "tasks/phase2_development_agent_contract_v2.json",
        )

    def test_conditional_terminal_configs_keep_single_variable_steps(self):
        r10g = load_experiment_config(ROOT / "configs" / "phase2" / "r10g_observation_fix.yaml")
        r10h = load_experiment_config(
            ROOT / "configs" / "phase2" / "r10h_terminal_answer_observation_fix.yaml"
        )
        r10i = load_experiment_config(
            ROOT / "configs" / "phase2" / "r10i_terminal_answer_bounded_retry.yaml"
        )

        self.assertFalse(r10g.inference.terminal_answer_enabled)
        self.assertTrue(r10h.inference.terminal_answer_enabled)
        self.assertEqual(r10g.inference.retry_prompt_mode, "legacy")
        self.assertEqual(r10h.inference.retry_prompt_mode, "legacy")
        self.assertEqual(r10i.inference.retry_prompt_mode, "bounded")
        self.assertEqual(r10h.browser.observation_mode, "visible_testids")
        self.assertEqual(r10i.browser.observation_mode, "visible_testids")


if __name__ == "__main__":
    unittest.main()
