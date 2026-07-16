from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from finetune.train_qlora import _assert_fully_gpu_resident, _json_sha256, _resume_checkpoint_step


class TrainQloraInfrastructureTests(unittest.TestCase):
    def test_formal_training_rejects_non_cuda_device_maps(self) -> None:
        self.assertEqual(_assert_fully_gpu_resident({"": 0}), {"": "cuda:0"})
        for device_map in (None, {}, {"": "cpu"}, {"layer": "disk"}, {"layer": "meta"}):
            with self.subTest(device_map=device_map):
                with self.assertRaises(RuntimeError):
                    _assert_fully_gpu_resident(device_map)

    def test_run_identity_digest_is_order_independent(self) -> None:
        self.assertEqual(_json_sha256({"a": 1, "b": 2}), _json_sha256({"b": 2, "a": 1}))

    def test_resume_checkpoint_must_be_direct_named_child_with_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            checkpoint = output / "checkpoint-50"
            (checkpoint / "adapter").mkdir(parents=True)
            (checkpoint / "training_state.pt").write_bytes(b"state")
            self.assertEqual(_resume_checkpoint_step(output, checkpoint), 50)

            nested = output / "nested" / "checkpoint-50"
            (nested / "adapter").mkdir(parents=True)
            (nested / "training_state.pt").write_bytes(b"state")
            with self.assertRaises(ValueError):
                _resume_checkpoint_step(output, nested)

    def test_resume_checkpoint_rejects_bad_name_and_missing_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            bad_name = output / "latest"
            (bad_name / "adapter").mkdir(parents=True)
            (bad_name / "training_state.pt").write_bytes(b"state")
            with self.assertRaises(ValueError):
                _resume_checkpoint_step(output, bad_name)

            missing_state = output / "checkpoint-50"
            (missing_state / "adapter").mkdir(parents=True)
            with self.assertRaises(FileNotFoundError):
                _resume_checkpoint_step(output, missing_state)


if __name__ == "__main__":
    unittest.main()
