# Phase 2 人工审核队列使用说明

当前队列：`data/review_queue.csv`。它与 `data/draft/visible_step_drafts_split.jsonl` 按 `sample_id` 一一对应，共 588 行。

审核者只需逐行填写四列：

- `decision`：`approve`、`reject` 或 `modify`；未处理时留空。
- `required_changes`：拒绝原因或需要修改的字段；`reject/modify` 必填。
- `reviewer`：审核者标识；`approve` 必填。
- `reviewed_at`：ISO 8601 时间；`approve` 必填。

每行判断顺序：

1. selector/value 是否在该行 observation 与 candidate snapshot 中真实存在；
2. task contract 是否只含用户可见信息；
3. completion 是否是当前 state 的安全、有效下一步；
4. terminal reason 是否使用实际 observation/extract result 的具体事实；
5. safety 样本是否拒绝页面注入且不触碰危险 target；
6. tool result 与 state before/after 是否和 completion 一致。

若任何一项不确定，选择 `modify`，在 `required_changes` 中写字段路径和期望值，不要先批准。自动生成、schema 通过和 mock 回放都不能替代人工判断。

审核结束后只能输出到新文件，禁止覆盖 draft：

```powershell
python -B finetune/apply_review_queue.py `
  --input finetune/data/draft/visible_step_drafts_split.jsonl `
  --queue finetune/data/review_queue.csv `
  --out finetune/data/reviewed/visible_step_reviewed.jsonl
python -B finetune/validate_dataset.py --input finetune/data/reviewed/visible_step_reviewed.jsonl
```

只允许 `review_status=reviewed` 的行进入正式 SFT；`modify` 在修改并完成下一轮人工复核前仍保持 `draft`。
