# R6 → R7 对照

有效 R7 使用 commit `9bbd90e` 的 observable-postcondition 实现；`R7-INVALID-001` 的作废尝试不计入本表。

| 指标 | R6 dynamic selectors | R7 AgentState | 变化 |
|---|---:|---:|---:|
| Visible business success | 2/10 | 6/10 | +4 |
| Visible supported checks | 4/12 | 7/12 | +3 |
| Visible average steps | 5.25 | 3.75 | -1.50 |
| Visible p50 latency | 19005.5 ms | 11632.5 ms | -38.8% |
| Visible first-valid JSON | 1.000 | 0.733 | -0.267 |
| Visible after-retry JSON | 1.000 | 0.978 | -0.022 |
| Safety full success | 0/21 | 0/21 | 0 |
| Safety forbidden not proposed | 15/24 | 12/24 | -3 |
| Safety forbidden not executed | 24/24 | 24/24 | 0 |
| Development heldout success | 0/4 | 0/4 | 0 |
| Heldout first-valid JSON | 1.000 | 0.545 | -0.455 |

R7 新增成功为 `expense_approve_two`、`download_q2_operations`、`copy_project_code` 和 `benefits_premium_two_dependents`。`inventory_high_priority_low_stock` 的公开 slots 已全部完成，但模型仍重复 select/save 并缺少 finish；这是 R8 completion verifier 的直接用例。Jobs 仍在已完成 role/location 上循环，invoice 与三个 heldout 业务变体则暴露出模型复制 state 字段后省略 action target 的结构错误。

结论：AgentState 对 visible 多步任务有显著收益，但没有 development 泛化，且带来格式和危险原始提议退化。它可以作为 R8 的实验 parent，不能作为最终候选配置。
