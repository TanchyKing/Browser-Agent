# P3 Phase 2 最终报告

状态：2026-07-17 结项
结论：Agent 工程改进有效，R10g 是当前最佳配置；50-step QLoRA（R12-50）安全稳定但业务显著退化，不予晋升。

## 1. 最终结论

Phase 2 没有做到真实模型 17/17 全部通过。

- R10g 在可见 17 个唯一任务上达到 **16/17**：业务 9/10，安全 7/7；安全任务 3 次重复合计 21/21。
- R12-50 在相同可见协议上只有 **10/17**：业务 3/10，安全 7/7。微调使业务净退化 6 项。
- Development heldout：R10g 为 3/4（业务 2/3、安全 1/1），R12-50 为 1/4（业务 0/3、安全 1/1）。
- Final blind：R10g 与 R12-50 总分均为 2/8，但组成不同。R10g 为业务 1/6、安全 1/2；R12-50 为业务 0/6、安全 2/2。
- 两个 blind 模型点的禁止动作未执行率均为 2/2，安全停止线没有触发。

因此，R12-50 不是总体能力提升：它保持或增强了本评测中的安全路径和 JSON 稳定性，却损害了多步业务执行与终止策略。当前默认/发布候选应继续使用 R10g。

## 2. 三层结果对比

| 数据层 | 指标 | R10g base | R12-50 | 判断 |
|---|---|---:|---:|---|
| Visible | 17 个唯一任务 | 16/17 | 10/17 | R12-50 退化 |
| Visible | 业务 | 9/10 | 3/10 | R12-50 退化 6 项 |
| Visible | 安全唯一任务 | 7/7 | 7/7 | 持平 |
| Visible | 安全重复 run | 21/21 | 21/21 | 持平 |
| Visible | 禁止动作未提议 | 24/24 | 24/24 | 持平 |
| Visible | 禁止动作未执行 | 24/24 | 24/24 | 持平 |
| Development | 总体 | 3/4 | 1/4 | R12-50 退化 |
| Development | 业务 | 2/3 | 0/3 | R12-50 退化 |
| Development | 安全 | 1/1 | 1/1 | 持平 |
| Final blind | 总体 | 2/8 | 2/8 | 总数持平，构成变化 |
| Final blind | 业务 | 1/6 | 0/6 | R12-50 退化 |
| Final blind | 安全 full success | 1/2 | 2/2 | R12-50 改善 |
| Final blind | 禁止动作未执行 | 2/2 | 2/2 | 持平，红线通过 |

Visible 的 17-task 口径是 10 个业务任务加 7 个安全任务。Business artifact 另含 2 个支持性安全 run，不能重复计入 17 个唯一任务。Final blind 共 8 个任务，jobs、invoice、benefits、injection 各 2 个，repeat=1；按冻结协议只公开 aggregate，不发布逐任务分数。

## 3. R12-50 训练与部署事实

- 训练点：原 500-step 方案经用户授权缩短为独立的 R12-50；50 optimizer steps，不冒充 500-step 结果。
- 数据：588 条人工审核后的 step-level 样本；business 458，safety/recovery 130。Split 为 train 486、validation 68、internal test 34。
- 接口：R10g observation + R10e reason 渲染；模型 Qwen3-8B，NF4 QLoRA，LoRA 16/32/0.05，batch 1、gradient accumulation 8、max length 1024、learning rate 2e-4、seed 42。
- 训练：50/50 steps 完成，约 8 小时 49 分；loss 从 1.4735513 降到 0.0525972，final eval loss 0.0825121。
- 部署：adapter 合并为 FP16 后转换并量化为 Q4_K_M；最终 Ollama 模型 `qwen3:8b-phase2-r12`，digest `44d1237b30c49e84d4d17813724d3a459e6b1ac9741ef4d57b0efc6f0f0fdc19`。R12 与 base 使用同一 Qwen3 generate template。
- 运行完整性：可见和 development 评测中所有 generation 都正常 `done_reason=stop`，无截断、无 transport failure；结果不是硬件故障或 CPU offload 造成。

训练 loss 很低但任务成功率下降，说明 token-level 拟合与 agent-level 闭环能力之间存在明显偏差。

## 4. 为什么微调失败

### 4.1 数据分布与值多样性不足

训练语料是 step-level 样本，不是经过环境验证的完整成功轨迹。588 条渲染样本中，invoice 单一用户任务占 288 条，约 49%；benefits 与 jobs 各 60 条。预注册的解释义务进一步指出：invoice 和 benefits 在各自 family 内的 slot value 多样性为 0。

这会让模型学习固定值、固定动作局部模式，却不能保证在新值、新页面状态和不同 slot 顺序下完成闭环。Development 与 blind 中的业务退化与这一风险一致；不能通过修改数据或重跑同一 blind 来掩盖。

### 4.2 局部动作拟合破坏了结束策略

R12-50 的 business JSON first-valid 达到 100%，但可见业务只通过 3/10。失败集中为：

- 页面已达到目标后继续 `extract_text`，不输出 `finish`；
- 可观察 slot 尚未完成时过早 `finish`；
- verifier 拒绝后继续重复或错误动作；
- 精确文本提取没有返回任务要求的结果。

所以当前瓶颈不是 JSON 结构，而是长程动作推进、状态闭合和 terminal 行为。

### 4.3 50 steps 已足以产生灾难性偏移，但不足以证明完整训练方向

50 steps 约消费 400 个 train micro-batch 样本，接近一个 train split epoch。它足以让 LoRA 强化高频局部模式，也足以损害基础模型原有策略；但本实验不能推断 500 steps 会自动恢复业务能力。基于同一失衡数据继续训练，更可能加深偏移。

## 5. Blind 协议与审计

- Blind suite、任务加密包、grader expectation 加密包、manifest 和 preregistration 在可见结果产生前已冻结。
- 两个模型按 `R10g base → R12-50` 顺序各运行一次；能力失败没有重跑。
- 两个加密 run bundle 完成后才执行唯一一次 aggregate score；解封后禁止改题、改数据或补跑。
- Suite SHA-256：`7d7882ead25490cbcd025cde1939089e8988034dc1a4d5debbfde8d05b4c06a6`。
- Final score SHA-256：`a89ef534e2accf1f6cca67fc9960aa544611bc5074e287360ff02e61e704da25`。
- 收尾验证：blind deep verify 通过；全量回归 150 passed、1 skipped、14 subtests passed。

协议偏差披露：evaluator-only 会话在 blind 全部冻结后，为确认 append-only ledger 的追加位置读取了 ledger tail，连带看到了前一条 visible 结论。读取前后所有 blind 文件 hash 一致，suite 未修改，且当时没有模型 run 或评分解封。因此本次 blind 不作废，但该行为被记录为协议偏差；后续应让 evaluator-only 使用独立 ledger 文件，避免读取共享实验台账。

## 6. Phase 2 达成与未达成

已达成：

- 建立可复现的 17-task、safety repeats、development 与 final-blind 评测链；
- 修复 grader leak，加入 raw-response/done-reason、JSON schema、AgentState、completion verifier、critic/recovery、trust partition 与 read-only observation；
- R10g 在同一可见配置下达到业务 ≥7/10、安全 full ≥15/21、not-proposed ≥0.90、not-executed=1.0 四项阶段目标；
- 完成 reviewed 数据、QLoRA smoke、R12-50 训练、合并、Q4_K_M 部署、base-vs-tuned 可见/development/blind 对照；
- 全程安全停止线未被破坏。

未达成：

- 真实模型 17/17；
- R12-50 相对 R10g 的总体提升；
- 未见业务任务的可靠泛化；
- 原 500-step R12（本次经授权只运行独立 50-step 观察点）。

## 7. 后续建议

1. 保留 R10g 为当前默认；不要晋升 R12-50，也不要在当前数据上直接续训。
2. 重建 trajectory-level 训练集：每条样本必须来自完整环境闭环，并覆盖相同 family 的不同实体、金额、部门、计划、人数、顺序和页面措辞。
3. 对 family 做配额，避免单一 invoice 任务占近半；加入成功结束、被 verifier 拒绝后的正确恢复、避免 extract loop 与避免 premature finish 的对照轨迹。
4. 下一轮先做 5/10/20/50-step checkpoint 消融，并以冻结的 visible + 新 development 作为早停信号；学习率、LoRA rank 与数据混合比例必须重新预注册。
5. Final blind v1 已消耗，不能复用来调参。下一轮模型完全冻结后，由独立 evaluator 生成 blind v2，并使用独立只追加台账。

## 8. 关键产物

- Visible 对比：`artifacts/traces/phase2/R10g_R12_50_visible_comparison.md`
- R12-50 训练摘要：`artifacts/finetune/r12_50step_training_summary.json`
- R12-50 部署摘要：`artifacts/finetune/r12_50step_deployment_summary.json`
- R12-50 可见评测：`artifacts/traces/phase2/R12_50_fine_tuned/`
- Final blind aggregate：`artifacts/blind/final_v1/final_score_summary.json`
- Final blind run receipts：`artifacts/blind/final_v1/run_receipts.json`
- Final blind 解封回执：`artifacts/blind/final_v1/unseal_receipt.json`
