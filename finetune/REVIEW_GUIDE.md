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
