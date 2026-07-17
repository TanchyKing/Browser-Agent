"""CPU-capable LoRA merge. Model loading can require about 16 GB system RAM."""

from __future__ import annotations

import argparse


def merge_adapter(base_model_path: str, revision: str, adapter_path: str, output_path: str) -> None:
    """Merge one LoRA adapter into a frozen base model entirely on CPU."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cpu_device_map = {"": "cpu"}
    base = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        revision=revision,
        torch_dtype=torch.float16,
        device_map=cpu_device_map,
        low_cpu_mem_usage=True,
    )
    # PEFT otherwise re-infers an "auto" map when the base has an hf_device_map
    # containing CPU. On memory-constrained hosts that silently selects disk
    # offload and then fails because this frozen merge path has no offload dir.
    merged = PeftModel.from_pretrained(
        base,
        adapter_path,
        device_map=cpu_device_map,
    ).merge_and_unload()
    merged.save_pretrained(output_path, safe_serialization=True, max_shard_size="4GB")
    AutoTokenizer.from_pretrained(adapter_path).save_pretrained(output_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="Qwen/Qwen3-8B")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    merge_adapter(args.base_model, args.revision, args.adapter, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
