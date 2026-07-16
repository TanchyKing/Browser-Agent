# Phase 2 fine-tune preparation

WP4 only prepares data and scripts. QLoRA, merge, GGUF conversion and Ollama import are GPU/disk gates and are not run during engineering setup.

Data pipeline:

```powershell
python -B finetune/export_mock_traces.py --runs artifacts/tmp/phase2/wp3_controller_slots_mock17_runs.json --out finetune/data/draft/mock_visible_steps.jsonl
python -B finetune/validate_dataset.py --input finetune/data/draft/mock_visible_steps.jsonl
python -B finetune/split_dataset.py --input finetune/data/draft/mock_visible_steps.jsonl --out finetune/data/draft/mock_visible_steps_split.jsonl
python -B finetune/prepare_sft.py --input finetune/data/draft/mock_visible_steps_split.jsonl --out finetune/data/processed/sft.jsonl --include-draft
```

Current grounded draft build (visible fixtures only):

```powershell
python -B finetune/build_draft_corpus.py `
  --config configs/phase2/r10g_observation_fix.yaml `
  --out finetune/data/draft/visible_step_drafts_split.jsonl `
  --review-queue finetune/data/review_queue.csv `
  --manifest finetune/data/draft/visible_step_drafts_manifest.json
python -B finetune/validate_dataset.py --input finetune/data/draft/visible_step_drafts_split.jsonl
```

This build is deterministic and remains entirely `draft`. See `REVIEW_QUEUE_GUIDE.md`; do not run `prepare_sft.py` for training until a separate reviewed dataset exists.

The canonical review dataset stores interface-neutral `semantic_completion` fields. After human review, render the same approved semantics to either deployment interface:

```powershell
python -B finetune/prepare_sft.py --input finetune/data/reviewed/visible_step_reviewed.jsonl --out finetune/data/processed/sft_r10e.jsonl --interface r10e
python -B finetune/prepare_sft.py --input finetune/data/reviewed/visible_step_reviewed.jsonl --out finetune/data/processed/sft_r10f.jsonl --interface r10f
```

The 588-row corpus uses R10g visible-testid observations. It must not be described as a replay of the frozen pre-fix R10e artifact.

Before training, create an isolated environment and run `preflight.py`. The current base Python environment intentionally does not contain the training stack.

```powershell
python -m venv .venv-finetune
.venv-finetune\Scripts\python -m pip install -r finetune/requirements-lock.txt
.venv-finetune\Scripts\python finetune/preflight.py
```

On Windows/Blackwell the lock file resolves `torch==2.7.1+cu128` from the
official PyTorch CUDA 12.8 index. A report showing `torch_cuda: null` or
`cuda_available: false` is a hard failure, even if every package is installed.
The training entrypoint uses a PyTorch `DataLoader` and PEFT directly; it does
not require PyArrow, `datasets`, or TRL.

GPU Gate commands (run only after reviewed data, R10 freeze and disk check):

```powershell
.venv-finetune\Scripts\python finetune/train_qlora.py --model Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 --dataset finetune/data/processed/sft_r10e_reviewed.jsonl --output-dir artifacts/finetune/R12_qwen3_8b_qlora --max-length 1024 --max-steps 500
.venv-finetune\Scripts\python finetune/merge_adapter.py --base-model Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 --adapter artifacts/finetune/R12_qwen3_8b_qlora/adapter --out artifacts/finetune/R12_qwen3_8b_qlora/merged
```

Convert the merged Hugging Face checkpoint with the pinned llama.cpp conversion tools, quantize to Q4_K_M, then place the GGUF next to `Modelfile.template` and run `ollama create`. Record llama.cpp commit, GGUF SHA-256 and Ollama model digest in the WP5 ledger.
