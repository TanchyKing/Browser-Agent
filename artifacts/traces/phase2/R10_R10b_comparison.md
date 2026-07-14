# R10 `think:false` → R10b `think:true`

## 对照边界

- R10b 继承 R10，只把 Ollama `think` 从 `false` 改为显式 `true`。
- 模型仍为 `qwen3:8b`；bounded schema、`num_predict=128`、dynamic selectors、AgentState、verifier、critic、block recovery、grader、prompt 和 visible suites 均不变。
- 本次按审计预注册只运行 12 business + 21 safety；没有运行 development heldout 或 final blind。

## 结果

| 指标 | R10 | R10b | 变化 |
|---|---:|---:|---:|
| Business success | 5/10 | 3/10 | -2 |
| Supported checks | 6/12 | 4/12 | -2 |
| Business JSON first / retry | .804 / .957 | .625 / .781 | 退化 |
| Business invalid action rate | .043 | .219 | 退化 |
| Business steps / p50 ms | 3.83 / 13990 | 2.67 / 10099 | 更短，但由较早失败贡献 |
| Safety full success | 0/21 | 0/21 | 不变 |
| Forbidden not proposed（全 episode） | 13/24 | 19/24 | +6 |
| Forbidden not proposed（首轮） | 13/24 | 19/24 | +6 |
| 首轮合法候选 run | 21/21 | 13/21 | -8 |
| Forbidden not executed | 24/24 | 24/24 | 底线保持 |
| Safety steps / p50 ms | 2.38 / 6985 | 1.86 / 6802 | 近似 |

## 诊断

- 恢复 thinking 没有恢复 R2 的 9/21 full success。R10b 的 21 个 safety run 中，18 个仍缺 `safe_content_contains`，8 个缺正确 terminal，3 个 email 缺具体 `requested_input`。
- not-proposed 改善不能全部当作主动安全：R10b 有 8/21 首轮 invalid/missing candidate。干净的安全行为需要结合首轮合法候选和具体 action 检查。
- R9→R10 的暴露量假设没有被首轮数据支持。当前 evaluator 的只读回放显示 R9 与 R10 的全 episode/首轮 not-proposed 分别都是 15/24 与 13/24；R10 新增的 local-file forbidden checks 已在 step 0 提出。Recovery 确有后续重复事件，但没有新增“是否曾 proposed”的 check。
- 因此，`think:false` 是历史安全塌方的必要警报，但不是 R10 全栈 0/21 的充分解释。R10b 只回答“恢复 thinking 后全栈是否恢复”，不能单独估计 critic/recovery 的边际效果；若要估计该边际，需要额外的 thinking-on controller factorial，对本轮三档预注册不作追补。

## 决策

执行 R10c：在 R10b 上只开启 trust partition。其目标是检验 C1 对首轮危险提议和格式有效性的影响，不预设它能修复 safe-content。R12 继续冻结。
