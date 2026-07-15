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
- Source: real Playwright replay of the 17 visible local fixtures under the frozen R10e public contract. Development heldout and final blind are excluded by both manifest and validator.
- Size: 588 unique step samples; business 458, safety/recovery 130 (22.1%). All 588 remain `draft`; reviewed 0, rejected 0.
- Split: train 486 / validation 68 / internal test 34. Business trajectory orderings and safety recovery contexts are indivisible templates; template split leakage is zero.
- Coverage: grounded target/value actions, multi-field ordering, missing/nested-field correction, safe-brief extraction and fact carry, generic-finish correction, hard-policy alternative behavior, and multiple-action JSON correction. No hidden chain-of-thought is stored.
- Validation: full Draft 2020-12 JSON Schema, unique IDs, selector grounding, holdout/blind exclusion and template split checks all pass 588/588. A second independent build produced the same dataset and queue hashes.
- Human gate: `data/review_queue.csv` has one blank decision row per sample. None is eligible for training until a human completes `REVIEW_QUEUE_GUIDE.md` and generates a separate reviewed output.

The original 53-row seed above is retained unchanged for audit history. The enhanced validator now rejects 11 of those historical rows for selector grounding, so it is deprecated and must not be concatenated with the current corpus.
