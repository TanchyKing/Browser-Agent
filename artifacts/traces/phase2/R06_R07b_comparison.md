# R6 → R7b 无泄漏对照

R7b 是 AgentState 的正式结果；旧 R7 因预填隐藏跨页值而 invalid，不参与本表。

| 指标 | R6 dynamic selectors | R7b AgentState | 变化 |
|---|---:|---:|---:|
| Visible business success | 2/10 | 4/10 | +2 |
| Visible supported checks | 4/12 | 5/12 | +1 |
| Visible average steps | 5.25 | 3.50 | -1.75 |
| Visible p50 latency | 19005.5 ms | 11267.0 ms | -40.7% |
| Visible first-valid JSON | 1.000 | 0.738 | -0.262 |
| Visible after-retry JSON | 1.000 | 0.952 | -0.048 |
| Safety full success | 0/21 | 0/21 | 0 |
| Safety forbidden not proposed | 15/24 | 15/24 | 0 |
| Safety forbidden not executed | 24/24 | 24/24 | 0 |
| Development heldout overall | 0/4 | 1/4 | +1 |
| Development heldout business | 0/3 | 1/3 | +1 |

R7b 的 visible 新增成功是 `expense_approve_two` 与 `download_q2_operations`；heldout 新增成功是 `heldout_invoice_platform_ops`。跨页 copy 在没有预填答案后失败，证明旧 R7 的该成功不可采信。Inventory 的 slots 已完成但仍 missing finish，保留为 R8 completion verifier 的目标用例。

结论：无泄漏 AgentState 带来较小但真实的 visible 提升和一条开发变体泛化，并保持 R6 的安全未提出/未执行指标；代价是结构有效率下降。R7b 可作为 R8 的有效 parent，仍不是最终候选。
