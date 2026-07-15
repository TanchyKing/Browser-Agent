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
  --out finetune/data/draft/visible_step_drafts_split.jsonl `
  --review-queue finetune/data/review_queue.csv `
  --manifest finetune/data/draft/visible_step_drafts_manifest.json
python -B finetune/validate_dataset.py --input finetune/data/draft/visible_step_drafts_split.jsonl
```

This build is deterministic and remains entirely `draft`. See `REVIEW_QUEUE_GUIDE.md`; do not run `prepare_sft.py` for training until a separate reviewed dataset exists.

Before training, create an isolated environment and run `preflight.py`. The current base Python environment intentionally does not contain the training stack.

```powershell
python -m venv .venv-finetune
.venv-finetune\Scripts\python -m pip install -r finetune/requirements-lock.txt
.venv-finetune\Scripts\python finetune/preflight.py
```

GPU Gate commands (run only after reviewed data, R10 freeze and disk check):

```powershell
.venv-finetune\Scripts\python finetune/train_qlora.py --dataset finetune/data/processed/sft_reviewed.jsonl --output-dir artifacts/finetune/qwen3-8b-phase2 --max-length 1024 --max-steps 500
.venv-finetune\Scripts\python finetune/merge_adapter.py --adapter artifacts/finetune/qwen3-8b-phase2/adapter --out artifacts/finetune/qwen3-8b-phase2/merged
```

Convert the merged Hugging Face checkpoint with the pinned llama.cpp conversion tools, quantize to Q4_K_M, then place the GGUF next to `Modelfile.template` and run `ollama create`. Record llama.cpp commit, GGUF SHA-256 and Ollama model digest in the WP5 ledger.
