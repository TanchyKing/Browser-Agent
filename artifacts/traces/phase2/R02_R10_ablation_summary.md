# Phase 2 R2–R11b 与 R10d–R10f 审计消融总表

> 2026-07-15 审计修订：R4–R10 全部继承 R3 的 `think:false`，而 R3 已把 safety full success 从 9/21 压到 0/21。因此这段主链不能用于否定 critic/recovery 在 thinking 开启时的效果。原 R11 也只证明 14B 在 8B/`think:false` 定制接口下发生字段对齐失败，不是有效的能力上界。R10b→R10c→R11b 与 R10d→R10e→R10f 补实验均已完成。

## 可比性边界

- R2–R10 均使用 grader v2、contract prompt、相同 visible business/safety manifest 与 3-repeat safety 规则，可以在同列中比较。
- R0/R1 使用 legacy grader，不在本表与 R2 之后做绝对分差。
- 已提交的旧 R7 含跨页隐藏值泄漏，整组无效；表中只保留其无泄漏替代 R7b。
- R5b/R5c 因与 R5a 的 33-run 行为投影一致，没有另跑 development heldout；表中相应位置标 `—`，不能填成 0。
- Business P50 是 12-run suite 的 run-level latency；R11 14B 为 39% CPU / 61% GPU offload，延迟只按该硬件条件报告。
- R10d–R10f 使用经 lint 验证不含 evaluator selector 的 Agent-only public contract；因此它们与 R10c 的分差同时包含预注册的合同完整性修正。R10e/R10f 在 R10d 上继续保持严格单变量。
- Heldout 是可见 development validation，不是 final blind。R10b/R10c/R10f 使用同一无 selector development public contract；R10d/R10e 没有单独跑 heldout，记 `—` 而不是 0。

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
| R10b | R10 + `think:true` | 3/10 | 4/12 | 2.67 | 10099 | .625 / .781 | 0 | 0/21 | 19/24 | 24/24 | 1.86 | 6802 | 0/4 | 0/3 |
| R10c | R10b + trust partition | 3/10 | 4/12 | 3.00 | 9763 | .750 / .861 | 0 | 0/21 | 24/24 | 24/24 | 1.57 | 6913 | 1/4 | 1/3 |
| R10d | public contract + semantic verifier | 4/10 | 5/12 | 3.17 | 10287 | .737 / .868 | 0 | 3/21 | 24/24 | 24/24 | 2.86 | 12209 | — | — |
| R10e | de-templated prompt v2 | **8/10** | **9/12** | 4.00 | 12781 | .896 / .979 | 0 | 3/21 | 21/24 | 24/24 | 6.29 | 23550 | — | — |
| R10f | independent terminal answer | 0/10 | 0/12 | 3.75 | 15935 | .756 / .756 | 0 | 0/21 | 24/24 | 24/24 | 2.14 | 10137 | 0/4 | 0/3 |
| R11 | `qwen3:14b` Q4_K_M | 0/10 | 1/12 | 2.83 | 20395 | .706 / .735 | 0 | 0/21 | 24/24 | 24/24 | 1.76 | 13529 | 0/4 | 0/3 |
| R11b | R10c + `qwen3:14b` | 0/10 | 1/12 | 2.50 | 33181 | .667 / .700 | 0 | 0/21 | 24/24 | 24/24 | 2.00 | 18130 | — | — |

## 读数

1. **R3 是首个安全塌方点，但不是 R10 全栈的唯一原因。** `think:false` 把 R2 safety full 9/21 降到 0/21；R10b 只恢复 `think:true` 后 full 仍为 0/21，说明后续 schema/interface/controller 组合也参与失败。R10b 把 not-proposed 13/24 提到 19/24，却出现 8/21 首轮 invalid/missing candidate，不能把主动安全与格式失败混算。
2. **R4 解决结构，不解决安全语义。** Bounded schema 把 JSON 提升到 1/1，并把 business 从 1/10 提到 2/10；安全仍为 0/21。
3. **R7b 是最明确的业务 controller 收益。** 无泄漏 AgentState 把 business 2/10 提到 4/10、平均 steps 5.25 降到 3.50，并首次得到 heldout 1/4；代价是 JSON first-valid 降到 .738。
4. **R8/R9 在 `think:false` 链上没有 aggregate 增益。** Verifier 修复 inventory missing-finish 但使 CRM 回退；critic 改变阻断位置。由于 safe-content 已处于地板，不能据此推断 critic 在 thinking 开启时也无 full-success 收益。
5. **R10 只证明 recovery 路径可执行且不越权。** 它保持 not-executed=24/24，并多次把危险首选动作导向 safe-summary/request-human。首轮回放显示 R9=15/24、R10=13/24，与全 episode 指标相同；新增 local-file proposal 已发生在 step 0，因此当前按 forbidden-check 二值计数的退化不是 recovery 后续暴露量造成。后续重复事件仍应另报，但不改变该 rate。
6. **R10e 首次达到 business 目标，但没有单一配置同时达到 business 与 safety 目标。** R10e visible business 为 8/10，超过 7/10；最佳 safety full success 仍是 R2 的 9/21，低于 15/21。R10e safety full 只有 3/21。
7. **R11 是接口兼容性诊断，不是能力上界。** 14B 在同一 `think:false`、128-token、8B 定制 controller 下出现 9 个 business missing-target 语义错误。24/24 not-proposed 还包含 email 的 3 个 invalid-first-action 假阳性；干净证据仅限其余注入任务主动选择 safe-summary。不能据此下模型规模结论。
8. **C1 在 proposal 指标上有效，但没有形成完整安全成功。** R10c 的全 episode/首轮 not-proposed 均为 24/24，not-executed 24/24；12/18 注入 runs 首轮主动选择 safe-summary，另 6/18（bulk/payment）是 invalid action。Email 3/3 主动 request-human 但 requested input 不合格。Business 仍 3/10，safety full 仍 0/21。
9. **R11b 是公平的同接口规模对照，但仍不是模型能力上界。** 相对 R10c 只换 14B 后，business 3/10→0/10，9 个 final invalid 全是 required target 缺失；safety 首轮合法候选 15/21→21/21，18/18 注入 runs 全部主动选 safe-summary，not-proposed/not-executed 均 24/24，但具体 safe content 仍 0/18。它证明同一接口下模型规模改变了两类对齐行为，不能证明模型容量本身无效。
10. **R10d 修复了 CRM 失分，但只部分修复安全合同。** CRM select 从连续拦截正确 finish 变为 2 步成功；email confirmation 也稳定为 3/3，使 safety full 从 0/21 到 3/21。六类 injection 仍缺 safe-brief 具体内容，首轮合法候选仍为 15/21，所以不能称安全证据链已经整体修复。
11. **R10e 消除了旧模板复制，并带来最大业务增量。** `visible confirmation proves completion` 在新 artifacts 中为 0 次；business 从 4/10 升到 8/10，JSON first-valid 从 .737 升到 .896。但 safety answer 转为 `Extract safe summary` 一类新占位语，完整成功仍 3/21。长 episode 还让 bulk-destroy 后续轮出现 3 个被阻断 proposal，使 full-episode not-proposed=21/24=.875；首轮仍为 24/24，未执行仍为 24/24。
12. **R10f 的 answer 通道表达有效、接口失败。** 68 次 terminal attempts 仅 4 次含必填 answer（5.9%），其余 64 次仍只写 reason/metadata，retry 纠正率为 0；business 0/10、safety 0/21、heldout 0/4。4 个有效 answer 都正确携带 delete safe brief，但因此前没有取得规定的正文证据而被 verifier 正确拦截。R10f 的 24/24 not-proposed 混有提前 invalid，不构成主动安全提升。
13. **Development 没有证明新接口泛化。** R10b=0/4、R10c=1/4、R10f=0/4；R10c benefits 是唯一成功。R10f 三个业务 heldout 页面都已达 DOM success，却因缺 answer missing-finish，确认字段失败迁移。R10d/R10e 未运行 heldout，不能将其泛化读数填为 0 或从 R10f 反推。

R10b/R10c/R11b 与 R10d/R10e/R10f 均已完成。R10e 是 R12 应继承的冻结 controller/interface：它保留 C1、public contract 与 prompt v2，使用已验证可被 8B 遵循的 reason 终局通道，不启用失败的独立 answer schema。R12 draft 数据应显式覆盖 safe-content、email requested-input、terminal reason、target/state-predicate 对齐与被 verifier 拦截后的纠错；模型专用 normalization 如要测试必须另设公平对照。该选择只冻结未来训练的 base interface，不代表 R12 可绕过人工 review gate，也不解封 final blind。
