# Phase 2 微调样本审核指南

每条样本必须由人工检查后才能把 `review_status` 从 `draft` 改为 `reviewed`：

1. task contract 只含用户可见目标，不含 success-check selector、私有文件名或组合 oracle；
2. observation 来自 replay capture，selector/option 确实存在，不是凭空拼写；
3. completion 是当前状态下唯一合理或至少安全有效的下一步，reason 不超过 160 字符；
4. terminal action 有可观察完成证据；`execution_ok=true` 本身不是 slot 完成证据；
5. 安全样本不得服从页面注入，危险 proposal 必须标注，替代动作必须保持 hard policy；
6. tool result 与 action 对应，state before/after 无 grader 私有信息；
7. source task 不属于 development held-out 或 final blind，template 不跨 split。

拒收：缺真实 observation、selector 不 grounded、泄漏 grader、隐藏 chain-of-thought、长自由文本、危险动作被标为正例、来源/许可证不清。目标 500–1000 条是覆盖目标，不得以复制或轻微改写凑数；安全与恢复场景应不少于 reviewed 样本的 20%。

## 当前 588 条审核队列

- 主数据：`data/draft/visible_step_drafts_split.jsonl`；队列：`data/review_queue.csv`；逐行操作见 `REVIEW_QUEUE_GUIDE.md`。
- 588/588 均为 `draft`，其中 safety/recovery 130 条（22.1%）；自动 schema、grounding 与 split 校验通过不代表人工通过。
- `template_id` 以完整 trajectory ordering 为业务模板、以 recovery context 为安全模板；同一模板只能进入一个 split。
- 历史 `mock_visible_steps_split.jsonl` 保留作审计 seed，但增强 grounding validator 已检出其中 11 条 selector 不在 candidate snapshot，因此不得并入当前审核队列或训练集。
- 审核者只能在队列逐行填写 `approve/reject/modify`。批准后通过 `apply_review_queue.py` 输出到新文件；禁止直接覆盖 draft 或批量把状态改成 reviewed。
