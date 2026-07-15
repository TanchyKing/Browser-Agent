# WP3 控制器线台账

## [2026-07-14 19:36] WP3-FAIL-001 | cooldown 名称遮蔽
- 类型: FAILURE
- 失败命令: `python -B -m pytest tests/agent/test_controller.py tests/agent/test_safety_smoke.py tests/eval/test_runner.py tests/test_experiment_config.py -q`
- 退出码: 1
- 关键报错: `TypeError: 'tuple' object is not callable`；runner 的局部变量 `action_signature` 遮蔽了同名 helper。
- 修复: cooldown 写入统一调用现有 `_action_signature(action)`，移除未使用的同名 import。
- 恢复验证: 相同测试子集 48/48 通过。

## [2026-07-14 19:40] WP3-DONE | Controller Gate 前实现完成
- 类型: HANDOFF
- 组件: AgentState、observable slot verifier、重复动作 cooldown、trust partition、deterministic pre-action critic、policy block recovery。
- 安全边界: safety policy 未放松且仍为最终否决；审计链固定为 original candidate → critic decision → replacement → policy decision → executed action；evaluator 的 not-proposed 指标读取 original candidate。
- 完成判据: `execution_ok=true` 不会单独完成 slot；slot 必须匹配显式 action/value/target 语义或可观察 tool result/evidence。invoice smoke 在 finish 前 5/5 slots completed。
- 配置: controller 全部 feature flag 默认关闭；`wp3_controller_smoke.yaml` 只用于工程回归，不是正式 R-run。R3/R4/R5a/b/c 已建立继承式单变量配置；R6 必须等 R5 结果后再选择 parent，未提前伪定最优 cap。
- 验证: controller all-flags mock 17/17；legacy flags-off mock 17/17；与 Phase 1 规范化语义投影 0 mismatch；全量 pytest 通过（1 项环境相关测试 skipped）。
- GPU Gate: 未运行 R3–R10 正式套件。
- 下一步: WP5 先串行冻结 R1/R2，再运行 R3–R5；依据 R5 真实结果生成 R6 config，随后按 state/verifier/critic/recovery 单变量顺序生成 R7–R10 配置。工程线可继续 WP4 数据与训练管线准备，但不得启动训练。

## [2026-07-15 01:05] R10-CORRECTION | Recovery 覆盖 critic reject
- 类型: CORRECTION / VERIFY
- R9 实测发现原 block recovery 只处理 policy denial，而 critic 已提前把 9 个 visible forbidden candidates 终止为 `request_human`，导致这些 run 无法进入 R10/C3。
- 修复: 仅在 `block_recovery_enabled=true` 时，把 critic reject 记录为 `block_source=critic`、`policy_decision=not evaluated`、`executed_action=null`，写入 blocked state 并要求下一轮安全重规划；flag 关闭时保持 R9 replacement 行为不变。Policy denial 同步记录 `block_source=policy`。
- 验证: critic 与 policy 两条恢复单测通过；controller/serialization/evaluator/config 子集 61/61；全量 pytest 通过（1 skip）；全部 controller flags 的 mock suite 17/17 success。

## [2026-07-15 05:12] LEDGER-IMMUTABILITY-CORRECTION | 追认 9e5e52d 违反追加式规则
- 类型: FAILURE / CORRECTION
- 违规事实: 已推送 commit `9e5e52d` 把本文件既有 `R10-CORRECTION` 标题时间从 `01:16` 改为 `01:05`。该行为即使只校正时间也违反 §1.3 追加式台账规则。
- 处置: 保留 commit 历史并用本条声明原值与改后值；不再次编辑旧条目。

## [2026-07-15 05:12] C1-ABLATION-CORRECTION | 信任分区补正式实验槽位
- 类型: CORRECTION / DECISION
- 发现: `trust_partition_enabled` 已实现并有单测，但 R1–R11 所有正式配置均为 false；总计划把 C1 列为能力却没有分配 R 槽位，WP5 也未在运行前上报。
- 补链: R10b 继承 R10 仅恢复 `think:true`；R10c 继承 R10b 仅开启 `trust_partition_enabled=true`；R11b 继承 R10c 仅切换 `model_name=qwen3:14b`。三档各只运行冻结 visible 12 business + 21 safety，不查看 development heldout 或 final blind。
- 边界: 不给 14B 单独加入 metadata→target normalization；若需要，必须另设变量并给 8B 同配置对照。

## [2026-07-15 10:19] CONTENT-CONTRACT-FIX | Safe brief 证据链与 CRM 完成判据
- 类型: CORRECTION / IMPLEMENTATION / VERIFY
- 诊断: R10c 注入任务常 click safe-summary 后直接 finish，未 extract 真正的 safe-brief；CRM 已正确选中 Northstar Clinics，却因旧 `verified_selection` 合同强制额外 extract 而反复拒绝 finish。
- 修复: 新增独立公开合同文件。六个注入任务要求成功 `extract_text` 且 target 含 `safe-brief` 后才能 finish；CRM slot 改为 click 后检查公开 DOM `[data-testid='selected-customer'] == Northstar Clinics`。未修改 hard safety policy。
- 防泄漏: 合同文件不含 evaluator 的 safe-content 关键词；`read_task` 先应用 grader override，再以独立 public contract 整体替换 `agent_contract`，避免私有字段深合并残留。
- 验证: 单测证明 premature finish 会被拦截、实际 safe-brief extract 后放行、CRM click 的 observable postcondition 可完成 slot、私有 ORACLE 不进入公开合同。
- 边界: 该修复只作为 R10d 开关启用；R10c 及历史结果不重算。
