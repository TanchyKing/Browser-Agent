# Phase 2 R2–R11 冻结消融总表

## 可比性边界

- R2–R10 均使用 grader v2、contract prompt、相同 visible business/safety manifest 与 3-repeat safety 规则，可以在同列中比较。
- R0/R1 使用 legacy grader，不在本表与 R2 之后做绝对分差。
- 已提交的旧 R7 含跨页隐藏值泄漏，整组无效；表中只保留其无泄漏替代 R7b。
- R5b/R5c 因与 R5a 的 33-run 行为投影一致，没有另跑 development heldout；表中相应位置标 `—`，不能填成 0。
- Business P50 是 12-run suite 的 run-level latency；R11 14B 为 39% CPU / 61% GPU offload，延迟只按该硬件条件报告。

## 主结果

| Run | 唯一新增变量 | Business | Supported | B steps | B p50 ms | JSON first / retry | Trunc. | Safety full | Not proposed | Not executed | S steps | S p50 ms | Heldout | Heldout biz |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R2 | v2 grader + contract baseline | 1/10 | 4/12 | 3.50 | 107346 | .738 / .905 | .231 | 9/21 | 18/24 | 24/24 | 1.57 | 20801 | 0/4 | 0/3 |
| R3 | `think:false` | 1/10 | 3/12 | 4.25 | 25955 | .961 / .961 | 0 | 0/21 | 15/24 | 24/24 | 1.86 | 4067 | 0/4 | 0/3 |
| R4 | bounded schema | 2/10 | 4/12 | 5.25 | 20381 | 1 / 1 | 0 | 0/21 | 15/24 | 24/24 | 1.29 | 3893 | 0/4 | 0/3 |
| R5a | `num_predict=128` | 2/10 | 4/12 | 5.25 | 20402 | 1 / 1 | 0 | 0/21 | 15/24 | 24/24 | 1.29 | 3957 | 0/4 | 0/3 |
| R5b | `num_predict=256` | 2/10 | 4/12 | 5.25 | 20197 | 1 / 1 | 0 | 0/21 | 15/24 | 24/24 | 1.29 | 3941 | — | — |
| R5c | `num_predict=768` | 2/10 | 4/12 | 5.25 | 20194 | 1 / 1 | 0 | 0/21 | 15/24 | 24/24 | 1.29 | 3948 | — | — |
| R6 | dynamic selector enum | 2/10 | 4/12 | 5.25 | 19006 | 1 / 1 | 0 | 0/21 | 15/24 | 24/24 | 1.29 | 3831 | 0/4 | 0/3 |
| R7b | no-leak AgentState | 4/10 | 5/12 | 3.50 | 11267 | .738 / .952 | 0 | 0/21 | 15/24 | 24/24 | 1.43 | 4129 | 1/4 | 1/3 |
| R8 | completion verifier | 4/10 | 5/12 | 3.58 | 12452 | .791 / .930 | 0 | 0/21 | 15/24 | 24/24 | 1.43 | 4126 | 1/4 | 1/3 |
| R9 | pre-action critic | 4/10 | 5/12 | 3.58 | 12387 | .791 / .930 | 0 | 0/21 | 15/24 | 24/24 | 1.43 | 4060 | 1/4 | 1/3 |
| R10 | critic + policy recovery | 5/10 | 6/12 | 3.83 | 13990 | .804 / .957 | 0 | 0/21 | 13/24 | 24/24 | 2.38 | 6985 | 1/4 | 1/3 |
| R11 | `qwen3:14b` Q4_K_M | 0/10 | 1/12 | 2.83 | 20395 | .706 / .735 | 0 | 0/21 | 24/24 | 24/24 | 1.76 | 13529 | 0/4 | 0/3 |

## 读数

1. **最大安全退化发生在 R3，而不是 controller。** `think:false` 把 business p50 从 107346 ms 降到 25955 ms，truncation 从 .231 降到 0，但 safety full success 从 9/21 降到 0/21、not-proposed 从 18/24 降到 15/24。后续 R4–R10 从未恢复完整安全成功。全局关闭 thinking 不能作为最终安全配置；R11 后应单独预注册“高风险/安全任务保留 thinking”的路由消融。
2. **R4 解决结构，不解决安全语义。** Bounded schema 把 JSON 提升到 1/1，并把 business 从 1/10 提到 2/10；安全仍为 0/21。
3. **R7b 是最明确的业务 controller 收益。** 无泄漏 AgentState 把 business 2/10 提到 4/10、平均 steps 5.25 降到 3.50，并首次得到 heldout 1/4；代价是 JSON first-valid 降到 .738。
4. **R8/R9 没有 aggregate 增益。** Verifier 修复 inventory missing-finish 但使 CRM 回退；critic 改变阻断位置但没有减少 original forbidden proposals 或提高 full success。
5. **R10 的恢复是“路径成功、任务失败”。** 它保持 not-executed=24/24，并多次把危险首选动作导向 safe-summary/request-human；但答案缺具体安全事实，full success 仍 0/21，not-proposed 反而降到 13/24，延迟和步数上升。
6. **当前没有单一累计配置同时达到最佳 business 与 safety。** R10 的 visible business 最高为 5/10，但最佳 safety full success 仍是 R2 的 9/21。阶段目标 7/10 business、15/21 safety 尚未达到。
7. **R11 说明 interface 对齐比模型大小更关键。** 14B 把 forbidden not-proposed 提高到 24/24，却因 9 个 business missing-target 语义错误降到 0/10，heldout 也降到 0/4；更大模型不能直接替代 controller/action 表示改进。

R11 结果表明，安全 selector 判断受益于更强模型，但业务纠错、内容生成和结构对齐主要受当前 AgentState/action interface 限制。R12 微调若要有意义，训练样本必须显式覆盖这些失败接口，而不能只重复 mock 成功轨迹。
