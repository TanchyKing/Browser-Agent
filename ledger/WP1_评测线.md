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
- 下一步: 正式实验执行者必须先完成并冻结 R1，再运行 R2；R2 完成前不得启动 R3 能力消融。工程线可继续 WP3 的 feature-flag controller 实现与 mock 验证。
