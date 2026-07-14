# Initial Phase 2 training-trace dataset

- File: `data/draft/mock_visible_steps_split.jsonl`
- Source: a fresh 17-task mock replay after A0 + AgentState integration; historical Phase 1 artifact was not used to reconstruct missing model inputs.
- Size: 53 step samples; 53 include state; 13 safety samples (24.5%); 26 steps belong to the six Phase 1 failed business tasks and are labeled as correction sources.
- Split: train 26 / validation 16 / internal test 11. Assignment is deterministic by whole task family, so one family never crosses splits.
- Status: all samples are `draft`. They pass structural and leakage validation but are not approved for training until the checks in `REVIEW_GUIDE.md` are completed by a human reviewer.
- Exclusions: development held-out and final blind data are rejected by the validator and are absent from this dataset.

This is an initial seed, not the planned 500–1000 reviewed-sample corpus. Expansion must use real replay/captured observations for visible-task variants; duplicating samples or fabricating selectors is prohibited.
