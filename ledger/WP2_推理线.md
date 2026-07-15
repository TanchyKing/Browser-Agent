# WP2 推理线台账

## [2026-07-14 18:58] WP2-START | 落地计划复核与执行拓扑
- 类型: DECISION
- 做了什么: 对 Claude 落地计划进行主审和独立复核，修正单 worktree 并行、固定 suite、统一配置、训练 trace、critic 审计、held-out/blind 分层和重复动作完成判据；创建 `codex/phase2-implementation` 分支。
- 涉及文件: Phase2_评测驱动Agent优化计划.md, Phase2_落地计划.md
- 验证命令: git branch --show-current
- 验证结果: 当前分支为 `codex/phase2-implementation`。
- 产物: 修订后的总计划与落地计划。
- 下一步: 冻结 `ExperimentConfig` 接口和 12-run/7-task suite manifest。

## [2026-07-14 19:06] WP2-A0 | 统一配置、固定清单与推理审计日志
- 类型: IMPLEMENTATION
- 做了什么: 新增版本化 `ExperimentConfig`；冻结 Phase 1 的 12 个业务运行与 7 个安全任务清单；为四个 CLI 统一增加 `--config`，运行脚本增加 `--suite-manifest`；Ollama 的 `think`、输出格式、模型、端点、超时、温度和 `num_predict` 均改为显式配置。
- 审计字段: 保存每次模型尝试的脱敏请求预览与 SHA-256、动作 schema、raw response/thinking 预览与 SHA-256、`done_reason`、截断标记、token 计数、耗时、JSON 解析错误；步骤序列化补齐 reason、risk、metadata、result metadata 与 `requested_input`。
- 环境处理: 当前 Python 未安装 PyYAML；配置加载器先解析 JSON-compatible YAML，普通 YAML 仅在用到时按需导入 PyYAML，不阻塞现有环境。
- 验证命令: `python -B -m pytest -q`
- 验证结果: 76 passed, 1 skipped。
- 烟雾测试: `python -B scripts/run_demo.py --backend mock --task-id crm_select_northstar --config configs/phase2/r1_legacy.yaml ...`
- 烟雾结果: success，5 步完成；产物包含 config digest、模型身份与完整 A0 审计字段。
- 下一步: 做规范化 Phase 1 行为投影比较，确认 A0 只增加观测字段、不改变默认 agent 行为；随后交付 WP1 的 R2 grader/task contract 冻结基线。

## [2026-07-14 19:07] WP2-FAIL-001 | 当前环境缺少 PyYAML
- 类型: FAILURE
- 失败命令: `python -B -m pytest -q`
- 退出码: 1
- 关键报错: `ModuleNotFoundError: No module named 'yaml'`，导致 3 个测试模块收集失败。
- 处理: 配置加载器改为优先解析 JSON-compatible YAML；只有普通 YAML 语法才按需导入 PyYAML。`r1_legacy.yaml` 保持 YAML 合法，同时采用 JSON 子集语法。
- 恢复验证: 同命令随后全量通过。

## [2026-07-14 19:17] WP2-DONE | 推理线 Gate 前工作完成
- 类型: HANDOFF
- 完成内容: A0 日志与训练 trace；统一配置与固定 suite；`think`、schema、`num_predict`、严格 Pydantic 校验、动态 selector/option enum、bounded retry 开关；全部默认关闭并保留 legacy 行为。
- 规范化比较: 新旧 mock artifact 均为 17 runs；归一化 `policy_blocked` 的缺失值后，action/status/error/terminal/final_state 等语义投影 0 mismatch。
- Mock 回归: 17/17 success；固定 safety manifest 的 7×3 共 21/21 success；全量 pytest 通过（1 项环境相关测试 skipped）。
- 真实模型 smoke 1: legacy JSON/default think，1 次调用，`finish`、first-valid、`done_reason=stop`、`eval_count=41`。
- 真实模型 smoke 2: `think:false + bounded schema + num_predict=256`，1 次调用，`finish`、first-valid、`done_reason=stop`、`eval_count=18`。两个 smoke 仅验证管线，不计入实验。
- GPU Gate: 未运行 R1 正式 33-run 套件。
- R1 business 精确命令: `python -B scripts/run_task_suite.py --backend ollama --config configs/phase2/r1_legacy.yaml --suite-manifest configs/suites/phase1_qwen12.json --out artifacts/traces/phase2/R01_legacy_a0/business_runs.json --trace-dir artifacts/traces/phase2/R01_legacy_a0/business`
- R1 safety 精确命令: `python -B scripts/run_model_safety_eval.py --backend ollama --repeat 3 --config configs/phase2/r1_legacy.yaml --suite-manifest configs/suites/phase1_safety7.json --out artifacts/traces/phase2/R01_legacy_a0/safety_runs.json --trace-dir artifacts/traces/phase2/R01_legacy_a0/safety`
- 下一步: 正式实验执行者串行运行以上两条命令并做 A0 截断归因；工程线继续 WP1，完成 contract prompt 与 grader v2 后才能冻结 R2。

## [2026-07-15 10:19] WP2-TERMINAL-ANSWER | 去模板 prompt 与独立最终答案通道
- 类型: IMPLEMENTATION / VERIFY
- 做了什么: 新增默认关闭的 `prompt.action_template_version=v2` 与 `inference.terminal_answer_enabled`；v2 删除可复制的 finish few-shot，要求摘要来自实际 observation/extract result；terminal schema 将 `answer` 与短 action `reason` 分离，非终端动作禁止 answer。
- 兼容性: v1 prompt、legacy schema 和 reason→agent_answer 回退保持不变；旧配置不会接受或序列化 answer。新开关按 R10e、R10f 分开，避免 prompt 与 schema 收益混淆。
- 涉及文件: `src/llm/adapters.py`, `src/llm/structured_output.py`, `src/agent/actions.py`, `scripts/run_demo.py`, `configs/schema/action.terminal-answer.schema.json`。
- 验证: 聚焦配置/prompt/schema/helper/controller 测试 41/41；R10f mock 17/17。
- 下一步: 全量 pytest 后交 WP5，真实模型只按预注册 R10d→R10e→R10f 顺序运行。

## [2026-07-16 00:26] R10G-OBSERVATION-CONFIG | 显式隔离 evidence observation 模式
- 类型: IMPLEMENTATION / CORRECTION / VERIFY
- 原因: Stage 3 的 read-only data-testid observation 修复原为全局代码变化，导致当前 HEAD 下的 R10e 与历史 R10e artifact 不再同条件。新实验若只换 experiment id 会保留隐式代码版本混淆。
- 实现: 新增 `browser.observation_mode=interactive_only|visible_testids`；旧配置默认 `interactive_only` 且该默认字段不进入 snapshot，历史 R10c/R10e digest 保持不变。`run_demo` 和 draft builder 显式把模式传给 Playwright executor。
- 新条件: R10g=R10e+`visible_testids`；R10h=R10g+terminal answer；R10i=R10h+bounded retry。后三者逐级只改变一个行为变量，条件分支不自动运行。
- 验证: 配置投影测试证明 R10e→R10g 仅多 browser mode，R10g→R10h 仅 answer/schema，R10h→R10i 仅 retry；R10c frozen digest 仍为 `ab8bc302...afe1a0`；interactive-only/visible-testid Playwright 双模式测试通过。
- 边界: 未运行 Ollama/GPU；冻结 artifacts 未改。
