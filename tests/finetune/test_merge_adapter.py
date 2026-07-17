from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from finetune.merge_adapter import merge_adapter


class MergeAdapterTests(unittest.TestCase):
    def test_forces_cpu_map_for_base_and_peft_dispatch(self) -> None:
        calls: dict[str, object] = {}

        class FakeMerged:
            def save_pretrained(self, path: str, **kwargs: object) -> None:
                calls["merged_save"] = (path, kwargs)

        class FakePeftLoaded:
            def merge_and_unload(self) -> FakeMerged:
                return FakeMerged()

        class FakePeftModel:
            @staticmethod
            def from_pretrained(base: object, adapter: str, **kwargs: object) -> FakePeftLoaded:
                calls["peft"] = (base, adapter, kwargs)
                return FakePeftLoaded()

        class FakeBaseModel:
            @staticmethod
            def from_pretrained(path: str, **kwargs: object) -> object:
                calls["base"] = (path, kwargs)
                return object()

        class FakeTokenizerInstance:
            def save_pretrained(self, path: str) -> None:
                calls["tokenizer_save"] = path

        class FakeTokenizer:
            @staticmethod
            def from_pretrained(path: str) -> FakeTokenizerInstance:
                calls["tokenizer_load"] = path
                return FakeTokenizerInstance()

        fake_torch = types.ModuleType("torch")
        fake_torch.float16 = "float16"  # type: ignore[attr-defined]
        fake_peft = types.ModuleType("peft")
        fake_peft.PeftModel = FakePeftModel  # type: ignore[attr-defined]
        fake_transformers = types.ModuleType("transformers")
        fake_transformers.AutoModelForCausalLM = FakeBaseModel  # type: ignore[attr-defined]
        fake_transformers.AutoTokenizer = FakeTokenizer  # type: ignore[attr-defined]

        with patch.dict(
            sys.modules,
            {"torch": fake_torch, "peft": fake_peft, "transformers": fake_transformers},
        ):
            merge_adapter("base", "revision", "adapter", "output")

        self.assertEqual(calls["base"][0], "base")  # type: ignore[index]
        self.assertEqual(calls["base"][1]["device_map"], {"": "cpu"})  # type: ignore[index]
        self.assertEqual(calls["peft"][1], "adapter")  # type: ignore[index]
        self.assertEqual(calls["peft"][2]["device_map"], {"": "cpu"})  # type: ignore[index]
        self.assertEqual(calls["tokenizer_load"], "adapter")
        self.assertEqual(calls["tokenizer_save"], "output")


if __name__ == "__main__":
    unittest.main()
