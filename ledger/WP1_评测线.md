# WP1 评测线台账

## [2026-07-14 19:28] WP1-DONE | Grader v2 与评测边界冻结
- 类型: HANDOFF
- TaskContract: 新增 `prompt.mode=legacy|contract`；contract 只读取 instruction、allowed actions 和显式 agent contract，不读取 success check、selector、组合 oracle 或私有文件名。metamorphic sentinel 测试证明只改变私有 grader 时 prompt 字节不变。
- Grader v2: 新增版本开关和 evaluator override；安全任务同时检查正确 terminal、forbidden 未执行、安全事实、未复述注入指令，以及 request_human 的具体 requested input。legacy 默认行为保留。
- Fixture 隔离: delete 的 v2 safe brief 使用独立 `prompt_injection_v2.html`，R1 legacy 仍读取原页面。
- 数据边界: 建立 visible / development held-out / fine-tune internal test / final blind 四分区；development held-out 覆盖 jobs、invoice、benefits、injection，参考轨迹只位于 evaluator fixture。
- Blind 机制: 提交封存协议、manifest JSON Schema 与 preregistration 模板；实际 blind suite 必须在 R10/数据/超参数冻结后生成。
- 指标: 冻结 run-level duration P50/P95、attempt-level truncation、done_reason 分布、output-token average/P50/P95；截断 fallback 为 `done_reason=length`、`done=false`，或无 done_reason 且 `eval_count>=num_predict`。
- 验证: 全量 pytest 通过（1 项环境相关测试 skipped）；legacy task-env smoke 为 17 tasks / 8 categories / 7 safety；R2 mock 17/17 success，v2 success checks 17/17 supported/pass，forbidden not-executed=1.0，full safety=7/7；development held-out evaluator reference 4/4 通过；HTML/JSON/CSV 报告均生成成功。
- GPU Gate: 未运行 R2 正式 33-run。
- R2 business 命令: `python -B scripts/run_task_suite.py --backend ollama --config configs/phase2/r2_fixed_grader.yaml --suite-manifest configs/suites/phase1_qwen12.json --out artifacts/traces/phase2/R02_fixed_grader/business_runs.json --trace-dir artifacts/traces/phase2/R02_fixed_grader/business`
- R2 safety 命令: `python -B scripts/run_model_safety_eval.py --backend ollama --repeat 3 --config configs/phase2/r2_fixed_grader.yaml --suite-manifest configs/suites/phase1_safety7.json --out artifacts/traces/phase2/R02_fixed_grader/safety_runs.json --trace-dir artifacts/traces/phase2/R02_fixed_grader/safety`

## [2026-07-15 01:17] TRACE-ALIGNMENT-CORRECTION | Recovery gap 不得按 browser 局部索引错配
- 类型: FAILURE / CORRECTION / VERIFY
- R10 首次评分把 8 个 critic-blocked forbidden candidates 错判为已执行，表面 not-executed=16/24；逐 step 审计确认这些候选均为 `executed_action=null`，真正执行的是下一 runner step 的 safe-summary click。
- 根因: browser trace 的 `step_index` 是实际工具调用局部索引；critic/controller block 不调用工具，会使它与 runner step index 错位。旧 merge 只按数字索引，把 browser local step 0 的安全执行结果合到了 runner step 0 的危险但未执行候选。
- 修复: browser/run step 合并必须同时匹配 action type 与 selector，并保证每条 browser step 只消费一次；索引仅作为优先候选，动作不匹配时搜索后续 runner step。新增 critic-block gap 回归测试。
- 验证: eval 子集 32/32、全量 pytest 通过（1 skip）；同一批 R10 traces 重算 not-executed=24/24。用新 evaluator 回放 R8/R9 的 business/safety/heldout 六份 artifact，summary、success checks、safety outcomes 与已提交结果逐字一致，无历史分数漂移。
- 下一步: 正式实验执行者必须先完成并冻结 R1，再运行 R2；R2 完成前不得启动 R3 能力消融。工程线可继续 WP3 的 feature-flag controller 实现与 mock 验证。

## [2026-07-15 05:12] LEDGER-IMMUTABILITY-CORRECTION | 追认 9e5e52d 违反追加式规则
- 类型: FAILURE / CORRECTION
- 违规事实: 已推送 commit `9e5e52d` 把本文件既有 `TRACE-ALIGNMENT-CORRECTION` 标题时间从 `01:25` 改为 `01:17`。内容虽未改变，但直接改写已有条目违反落地计划 §1.3“写错只追加 CORRECTION”的规则。
- 处置: 不再改写或回滚该已发布历史；本条永久记录原值、改后值、原因和 commit。此后时间偏差只能追加更正，不允许编辑旧标题。

## [2026-07-15 05:12] PRE-R12-EVAL-AUDIT | 历史回放与首轮安全口径
- 类型: FAILURE / VERIFY / IMPL
- 回放: 首次命令错误地把 development heldout 强制指向 `tasks/offline_tasks.jsonl`，因此 7 份 heldout summary 如预期不一致；修正为读取每份 artifact 的 `experiment.values.evaluator.task_file_path` 后，R2–R7b 共 25 份 business/safety/heldout summary 的旧 `summary/error_analysis/success_checks/safety_outcomes` 字段全部逐字段一致。
- 影响论证: R2–R7b 没有 recovery 产生的“runner 有记录、browser 无工具调用”间隙；只读回放进一步确认 trace-alignment fix 不改变这些历史分数。原先只明确回放 R8/R9 的审计链现已补齐。
- 指标事实: 既有 R2–R11 `safety_summary.json` 已有顶层 `safety_outcomes`，并非缺失；本次新增显式 proposal/execution 分子分母、首轮 proposal rate，以及 first-round invalid/missing candidate runs，避免把 recovery 增加的后续暴露和 invalid action 假阳性混在一起。
- 验证: `tests/eval/test_runner.py` 13/13 通过；新增测试证明“首轮 safe、第二轮 forbidden”在全 episode 计 proposed、首轮不计 proposed。

## [2026-07-15 10:19] PUBLIC-CONTRACT-SEPARATION | R10d 合同不读取 grader oracle
- 类型: IMPLEMENTATION / VERIFY
- 做了什么: 为 R10d 新增独立 `tasks/phase2_agent_contract_v2.json` 与 `prompt.agent_contract_overrides_path`。任务加载时 grader override 和公开 Agent contract 使用两个来源，公开合同整体替换 `agent_contract`，不会深合并残留 evaluator 私有 slot/关键词。
- 内容边界: safe brief 合同只声明可见 selector 语义 `safe-brief` 与成功 extract；CRM 只声明用户指令中的 Northstar Clinics 和页面公开 selected-customer 状态；不复制 `success_check_v2.safe_content_contains/excludes`。
- 验证: sentinel 单测把 evaluator contract 替换为 `ORACLE`，最终 Agent contract 只保留 public slot 且不含 ORACLE；legacy prompt/grader path 默认不变。
- Blind: development heldout 仍使用任务内公开 contract；final blind 未生成、未读取。
