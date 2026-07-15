import json
import unittest
from pathlib import Path

from scripts.run_demo import read_task
from src.experiment_config import load_experiment_config


ROOT = Path(__file__).resolve().parents[1]


def _task_ids(path: Path) -> list[str]:
    return [
        str(json.loads(line)["task_id"])
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _selector_targets(task: dict) -> set[str]:
    success_check = task.get("success_check_v2") or task.get("success_check") or {}
    targets = {
        str(check.get("target"))
        for check in success_check.get("all_of") or []
        if check.get("target")
    }
    return {
        target
        for target in targets
        if target.startswith(("#", ".", "[")) or "data-testid" in target
    }


class AgentContractLeakTests(unittest.TestCase):
    def _assert_config_contracts_do_not_copy_evaluator_selectors(
        self,
        config_name: str,
    ) -> None:
        config = load_experiment_config(ROOT / "configs" / "phase2" / config_name)
        task_path = ROOT / config.evaluator.task_file_path
        for task_id in _task_ids(task_path):
            task = read_task(
                task_id,
                config.evaluator.task_file_path,
                config.evaluator.task_overrides_path,
                config.prompt.agent_contract_overrides_path,
            )
            contract = json.dumps(task.get("agent_contract") or {}, ensure_ascii=False)
            for selector in _selector_targets(task):
                self.assertNotIn(
                    selector,
                    contract,
                    msg=f"{task_id} copies evaluator selector {selector} into Agent contract",
                )

    def test_visible_r10d_contracts_do_not_copy_evaluator_selectors(self):
        self._assert_config_contracts_do_not_copy_evaluator_selectors(
            "r10d_contract_fixes.yaml"
        )

    def test_r10f_heldout_contracts_do_not_copy_evaluator_selectors(self):
        self._assert_config_contracts_do_not_copy_evaluator_selectors(
            "r10f_terminal_answer_heldout.yaml"
        )

    def test_r10g_and_conditional_contracts_do_not_copy_evaluator_selectors(self):
        for config_name in (
            "r10g_observation_fix.yaml",
            "r10g_observation_fix_heldout.yaml",
            "r10h_terminal_answer_observation_fix.yaml",
            "r10i_terminal_answer_bounded_retry.yaml",
        ):
            with self.subTest(config_name=config_name):
                self._assert_config_contracts_do_not_copy_evaluator_selectors(config_name)


if __name__ == "__main__":
    unittest.main()
