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
