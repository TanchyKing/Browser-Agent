# R10c 8B → R11b 14B 同接口规模对照

## 对照边界

- R11b 继承 R10c，解析配置除 `experiment_id` 外只改变 `model_name: qwen3:8b → qwen3:14b`。
- 两组均为 `think:true`、trust partition、bounded schema、`num_predict=128` 和相同 state/verifier/critic/recovery、grader、prompt、visible suites。
- 没有加入 14B 专用 normalization、few-shot 或 prompt；只运行 business 12 + safety 21，未运行 heldout/blind。
- 14B 实测 working set 10 GB、39% CPU / 61% GPU、约 6.9 GiB VRAM；延迟不与 8B 作硬件公平排名。

## 结果

| 指标 | R10c 8B | R11b 14B | 变化 |
|---|---:|---:|---:|
| Business success | 3/10 | 0/10 | -3 |
| Supported checks | 4/12 | 1/12 | -3 |
| Business JSON first / retry | .750 / .861 | .667 / .700 | 退化 |
| Business invalid action rate | .139 | .300 | 退化 |
| Business steps / p50 ms | 3.00 / 9763 | 2.50 / 33181 | offload 更慢 |
| Safety full success | 0/21 | 0/21 | 不变 |
| Forbidden not proposed（全 episode/首轮） | 24/24 / 24/24 | 24/24 / 24/24 | 不变 |
| 首轮合法候选 run | 15/21 | 21/21 | +6 |
| Forbidden not executed | 24/24 | 24/24 | 底线保持 |
| Safety steps / p50 ms | 1.57 / 6913 | 2.00 / 18130 | offload 更慢 |

## 原始行为审计

- R11b business 有 9 个 final `invalid_llm_response`，9/9 都是 action 需要顶层 target，但模型把 selector/state hint 放在 metadata/reason。全部 generation `done_reason=stop`、truncation=0，不是 token cap 或 transport 失败。
- R11b 的六个注入族 18/18 首轮都主动选择 safe-summary；email 3/3 首轮选择 request-confirmation，随后进入 request-human。21/21 都是合法首轮候选，因此 24/24 not-proposed 不再含“首轮 invalid 而安全”的假阳性。
- 仍有 18/18 注入 runs 缺 grader 要求的具体 safe content，email 3/3 缺具体 requested input；所以安全路径选择改善没有转化为 full success。

## 结论边界

这是有效的同接口模型变量对照：在 R10c 接口下，14B 的安全动作有效性优于 8B，但业务 target 字段对齐显著更差。它仍不是“模型能力上界”，因为 action contract 本身可能对不同模型存在适配偏差。可以得出的部署结论是：不能直接把 14B 替换进当前 Agent；若测试 metadata→target normalization，必须把 normalization 作为独立变量，并对 8B 和 14B 同时运行。

R12 继续停在人工 reviewed 数据门禁；final blind 未生成或运行。
