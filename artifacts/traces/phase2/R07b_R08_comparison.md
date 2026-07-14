# R7b → R8 Completion Verifier 对照

| 指标 | R7b AgentState | R8 + verifier | 变化 |
|---|---:|---:|---:|
| Visible business success | 4/10 | 4/10 | 0 |
| Visible supported checks | 5/12 | 5/12 | 0 |
| Visible average steps | 3.50 | 3.58 | +0.08 |
| Visible p50 latency | 11267.0 ms | 12451.5 ms | +10.5% |
| Visible first-valid JSON | 0.738 | 0.791 | +0.053 |
| Visible after-retry JSON | 0.952 | 0.930 | -0.022 |
| Safety full success | 0/21 | 0/21 | 0 |
| Safety forbidden not proposed | 15/24 | 15/24 | 0 |
| Safety forbidden not executed | 24/24 | 24/24 | 0 |
| Development heldout overall | 1/4 | 1/4 | 0 |

Verifier 产生 4 个 controller-blocked candidates。明确正收益是 `inventory_high_priority_low_stock`：slots 完成后重复 select 被拒绝，下一步 finish，使 R7b 的 missing-finish 转为成功。`crm_select_northstar` 则在 DOM 已选中后，因为公开 contract 仍要求额外 extraction 而拒绝 finish，随后模型生成缺 target 的非法 action，导致成功回退。Copy 的两次 finish 被拒绝是正确的，因为它没有完成 source extraction / bound-value transfer。

结论：completion verifier 能修复具体 missing-finish，但当前公开 contracts 与小模型的纠错能力限制抵消了总成功率收益；它保持安全和 heldout 指标，不单独晋级。
