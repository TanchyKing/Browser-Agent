# Artifact Manifest

Updated: 2026-06-23 00:15 CST.

## Canonical Artifacts

These files are the current display/evaluation evidence. Historical review
iterations are archived under `_legacy`.

| Purpose | Trace artifact | Eval artifact |
|---|---|---|
| CRM qwen3 minimal loop | `artifacts/traces/canonical_crm_ollama_run.json` | `artifacts/eval/canonical_crm_ollama_summary.json` |
| qwen3 12-task business/generalization run | `artifacts/traces/canonical_qwen_business_12_runs.json` | `artifacts/eval/canonical_qwen_business_12_summary.json` |
| Scripted safety policy check | `artifacts/traces/canonical_scripted_safety_runs.json` | `artifacts/eval/canonical_scripted_safety_summary.json` |
| 17-task deterministic mock suite | `artifacts/traces/review8_mock_suite_runs.json` | `artifacts/eval/review8_mock_suite_summary.json` |
| 7-task x3 model-driven prompt-injection benchmark | `artifacts/traces/review8c_model_safety_7tasks_runs.json` | `artifacts/eval/review8c_model_safety_7tasks_summary.json` |

## Demo Images

- `artifacts/demo/crm_success.png`
- `artifacts/demo/prompt_injection_bulk_destroy.png`
- `artifacts/demo/safety_guardrail_metrics.png`

## Legacy Archive

- `artifacts/eval/_legacy/`
- `artifacts/traces/_legacy/`

The archive keeps older review iterations for auditability. Do not use legacy
summaries as headline project metrics; several older safety files used earlier
metric semantics before `policy_block_rate` and `safety_violation_rate` were
split.
