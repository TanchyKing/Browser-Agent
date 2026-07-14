# R5 `num_predict` 对照

冻结条件：R4 bounded schema + `think:false` + contract prompt + v2 grader；仅改变 `num_predict`。每档独立执行 12 business-suite runs 与 21 safety runs。

| 指标 | 128 | 256 | 768 |
|---|---:|---:|---:|
| 纯 business 成功 | 2/10 | 2/10 | 2/10 |
| business supported pass | 4/12 | 4/12 | 4/12 |
| business 平均 steps | 5.25 | 5.25 | 5.25 |
| business p50 ms | 20,402 | 20,197 | 20,193.5 |
| business p95 ms | 25,412.15 | 25,415.6 | 25,499.15 |
| business JSON first-valid | 1.0 | 1.0 | 1.0 |
| business truncation | 0 | 0 | 0 |
| business done_reason=stop | 63/63 | 63/63 | 63/63 |
| safety 完整成功 | 0/21 | 0/21 | 0/21 |
| safety forbidden 未提出 | 15/24 | 15/24 | 15/24 |
| safety forbidden 未执行 | 24/24 | 24/24 | 24/24 |
| safety p50 ms | 3,957 | 3,941 | 3,948 |
| safety p95 ms | 9,640 | 9,670 | 9,796 |
| safety truncation | 0 | 0 | 0 |

归一化行为投影（task/status/terminal answer/逐步 action、target、value、reason、risk、valid、execution、policy block、error、requested input）在 128 vs 256、128 vs 768 的 business 与 safety 中均完全一致；只有 run id、时长和底层计时等非行为字段不同。

## DECISION

选择 `num_predict=128` 作为后续主链默认值：它是三档中最小值，未触发任何 length/truncation，且没有可观察行为或成功率损失。此决策只解决生成预算，不表示 R5 配置通过安全 gate；R5 的 safety 完整成功仍为 0/21，后续必须依靠 selector grounding、AgentState、completion verifier、critic 和 recovery 继续改进。
