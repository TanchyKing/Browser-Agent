from __future__ import annotations

import unittest

from finetune.probe_qlora_offline import (
    FORMAL_SCHEDULER_STEPS,
    GRADIENT_ACCUMULATION_STEPS,
    LORA_ALPHA,
    LORA_DROPOUT,
    LORA_R,
    PROBE_OPTIMIZER_STEPS,
    assert_fully_gpu_resident,
)


class OfflineProbeTests(unittest.TestCase):
    def test_accepts_only_cuda_device_map(self) -> None:
        self.assertEqual(assert_fully_gpu_resident({"": 0}), {"": "cuda:0"})
        self.assertEqual(
            assert_fully_gpu_resident({"model": "cuda:0", "lm_head": "0"}),
            {"model": "cuda:0", "lm_head": "cuda:0"},
        )

    def test_rejects_cpu_disk_and_missing_maps(self) -> None:
        for device_map in (None, {}, {"model": "cpu"}, {"model": "disk"}, {"model": "meta"}):
            with self.subTest(device_map=device_map):
                with self.assertRaises(RuntimeError):
                    assert_fully_gpu_resident(device_map)

    def test_probe_constants_match_frozen_formal_configuration(self) -> None:
        self.assertEqual(PROBE_OPTIMIZER_STEPS, 3)
        self.assertEqual(GRADIENT_ACCUMULATION_STEPS, 8)
        self.assertEqual(FORMAL_SCHEDULER_STEPS, 500)
        self.assertEqual((LORA_R, LORA_ALPHA, LORA_DROPOUT), (16, 32, 0.05))


if __name__ == "__main__":
    unittest.main()
