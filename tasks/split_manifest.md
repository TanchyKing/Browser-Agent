# Phase 2 数据与评测边界

| 分区 | 内容 | 可反复查看 | 可训练 | 用途 |
|---|---|---:|---:|---|
| Visible regression | `tasks/offline_tasks.jsonl` + Phase 1 固定 manifests | 是 | 仅其人工生成变体 | 回归与消融 |
| Development held-out | `tasks/development_heldout_tasks.jsonl` | 是 | 否 | 每轮泛化验证；不得称为 blind/hidden |
| Fine-tune internal test | 由 `finetune/` 按任务族切分 | 是 | 否 | 训练管线内部选择 |
| Final blind holdout | R10/controller/数据/超参数冻结后生成，仓库外封存 | 否 | 永不 | 只在预注册的 R10 与 R12 最终点运行 |

规则：任何进入 Agent prompt、few-shot、mock action、critic 规则或训练数据的样本都不再属于 held-out；development held-out 的参考轨迹只存在于 evaluator 测试夹具。最终 blind 结果不得用于返工 controller、grader、训练数据或超参数。
