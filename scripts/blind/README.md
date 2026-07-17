# Phase 2 evaluator-only final blind entry

The final blind task bodies, pages, grader expectations, and model-run traces
remain sealed. Commands print only non-sensitive counts, hashes, progress, and
receipts until the one-time aggregate scoring step.

Public verification (does not decrypt):

```powershell
python -B scripts/blind/evaluator_only.py verify
```

Evaluator-only integrity verification (decrypts in memory; prints no content):

```powershell
python -B scripts/blind/evaluator_only.py verify --deep
```

Frozen execution order:

```powershell
python -B scripts/blind/evaluator_only.py run --output-label R10g_base --model-name qwen3:8b
python -B scripts/blind/evaluator_only.py run --output-label R12_fine_tuned --model-name qwen3:8b-phase2-r12
```

After both encrypted run receipts exist, the following command performs the
single aggregate score reveal:

```powershell
python -B scripts/blind/evaluator_only.py score
```

Do not run `score` between comparison points. The entry point enforces model
digests, frozen controller/grader file hashes, repeat=1, execution order, the
bounded infrastructure-retry rule, and one-time scoring.

If and only if an exception abort is recorded before score reveal, the sole
full-point retry must be explicit:

```powershell
python -B scripts/blind/evaluator_only.py run --output-label <label> --model-name <model> --infrastructure-retry
```
