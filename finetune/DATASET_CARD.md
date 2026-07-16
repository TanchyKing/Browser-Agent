# Initial Phase 2 training-trace dataset

- File: `data/draft/mock_visible_steps_split.jsonl`
- Source: a fresh 17-task mock replay after A0 + AgentState integration; historical Phase 1 artifact was not used to reconstruct missing model inputs.
- Size: 53 step samples; 53 include state; 13 safety samples (24.5%); 26 steps belong to the six Phase 1 failed business tasks and are labeled as correction sources.
- Split: train 26 / validation 16 / internal test 11. Assignment is deterministic by whole task family, so one family never crosses splits.
- Status: all samples are `draft`. They pass structural and leakage validation but are not approved for training until the checks in `REVIEW_GUIDE.md` are completed by a human reviewer.
- Exclusions: development held-out and final blind data are rejected by the validator and are absent from this dataset.

This is an initial seed, not the planned 500–1000 reviewed-sample corpus. Expansion must use real replay/captured observations for visible-task variants; duplicating samples or fabricating selectors is prohibited.

## Current unattended draft corpus (2026-07-15)

- Primary file: `data/draft/visible_step_drafts_split.jsonl`; manifest: `data/draft/visible_step_drafts_manifest.json`.
- Source: real Playwright replay of the 17 visible local fixtures under the R10e controller/public contract plus the explicit R10g `browser.observation_mode=visible_testids` condition. Development heldout and final blind are excluded by both manifest and validator.
- Size: 588 unique step samples; business 458, safety/recovery 130 (22.1%). All 588 remain `draft`; reviewed 0, rejected 0.
- Split: train 486 / validation 68 / internal test 34. Business trajectory orderings and safety recovery contexts are indivisible templates; template split leakage is zero.
- Coverage: grounded target/value actions, multi-field ordering, missing/nested-field correction, safe-brief extraction and fact carry, generic-finish correction, hard-policy alternative behavior, and multiple-action JSON correction. No hidden chain-of-thought is stored.
- Semantic/interface boundary: every row has one interface-neutral `semantic_completion`. Human review checks `action_reason` and, for terminal rows, `user_visible_result` once. `prepare_sft.py --interface r10e` places the reviewed result in `reason`; `--interface r10f` renders a short reason plus `answer`. Interface serialization does not create a second human label.
- Observation dependency: the 588 rows were generated after the read-only `safe-brief` observation fix and therefore align with R10g. They do **not** reproduce the observation available in the already-frozen R10d/R10e/R10f model artifacts; comparisons must not treat those traces as if the evidence selector had been reachable.
- Validation: full Draft 2020-12 JSON Schema, unique IDs, selector grounding, holdout/blind exclusion and template split checks all pass 588/588. A second independent build produced the same dataset and queue hashes.
- Human gate: `data/review_queue.csv` has one blank decision row per sample. None is eligible for training until a human completes `REVIEW_QUEUE_GUIDE.md` and generates a separate reviewed output.
- Post-R10g interface decision (2026-07-16): R10g achieved business 9/10 and safety full 21/21 with the existing `reason` terminal channel; the remaining failures were not missing-answer failures. Therefore the current R12 baseline uses `visible_testids` observations and the `r10e` reason rendering. The `r10f` answer rendering remains a reversible research view only and is not the selected training/deployment interface.

The original 53-row seed above is retained unchanged for audit history. Under the pre-semantic schema, enhanced grounding validation rejected 11 rows. The current schema additionally requires `semantic_completion`, which that historical file does not contain. It remains deprecated and must not be concatenated with the current corpus.

## Review record (2026-07-16)

- Reviewer: `claude-fable-5`, acting as the project's independent auditor under **explicit user delegation given in chat on 2026-07-16**. This is a delegated AI review, not a review performed personally by the project owner; the owner retains the right to spot-check and revoke approvals. The reviewer is independent of the corpus generator (Codex).
- Method: all six REVIEW_QUEUE_GUIDE criteria were executed as programmatic checks over 588/588 rows (target/option grounding against each row's observation+candidate snapshot; contract-leak scan against evaluator success checks; terminal-fact grounding of `semantic_user_visible_result` tokens against observation/tool_result/state; forbidden-target scan for safety rows; type/select value consistency against contract/state 270/270; template-split integrity 0 leaks), plus manual full-sample reading of a stratified selection across the 71 (task, action, correction, safety) strata and all 17 unique terminal results. All checks passed; decision `approve` 588/588; reviewed output regenerated and revalidated (`valid 588/588`, 0 leaks).
- Findings recorded with approval (corpus-level, not per-row defects):
  1. **Zero slot-value diversity** — every invoice row uses Acme Analytics/INV-2048/1280, every benefits row Jordan Lee/Premium/2. The learned behavior may be value memorization instead of contract→field copying; post-SFT heldout results must be read with this risk in mind, and a value-variant expansion (through this same queue) is recommended before any second training round.
  2. **Family mislabel** — 60 benefits-goal rows carry `family=invoice_form`. Metadata-only defect; split integrity is by `template_id` and is unaffected.
  3. Injection variants differ in wording only; internal validation/test splits therefore measure wording-robustness, not layout generalization. Layout generalization remains the job of development heldout and final blind.
