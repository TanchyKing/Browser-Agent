# WP4 微调准备台账

## [2026-07-14 19:44] WP4-DATA | 初始 replay 数据导出
- 类型: IMPLEMENTATION
- 来源: `artifacts/tmp/phase2/wp3_controller_slots_mock17_runs.json`，这是 A0/AgentState 合并后的 fresh replay；未用历史 artifact 反推缺失 observation。
- 结果: 53 个 step samples；state 53/53；安全 13/53（24.5%）；Phase 1 六个失败业务任务相关 correction steps 26；train/validation/internal-test = 26/16/11。
- 验证: 导出后与 split 后各运行一次 `validate_dataset.py`，均为 53 valid / 0 failure；全量 pytest 通过（1 项环境相关测试 skipped）。
- 状态: 全部保持 `draft`，未冒充人工审核完成；development held-out/final blind 未进入数据。

## [2026-07-14 19:45] WP4-FAIL-001 | 隔离训练环境依赖尚未安装
- 类型: FAILURE
- 失败命令: `.venv-finetune\Scripts\python finetune/preflight.py`
- 退出码: 1
- 关键结果: disk free 175.09 GB；torch/transformers/trl/peft/accelerate/bitsandbytes/datasets 均 missing，`ready=false`。
- 解释: 工程环境按计划与训练环境隔离；未下载数十 GB checkpoint，也未启动 GPU Gate。版本已锁定在 `requirements-lock.txt`，安装后必须重新运行 preflight 并记录 CUDA/Blackwell/bitsandbytes 实测结果。

## [2026-07-14 19:46] WP4-HANDOFF | 训练 Gate 前准备完成
- 类型: HANDOFF
- 已交付: step JSON Schema、A0 trace exporter、结构/泄漏 validator、任务族 split、防交叉测试、SFT formatter、人工审核指南、锁定依赖、环境/CUDA/disk preflight、QLoRA/merge/Ollama 模板。
- 未完成且不得伪称完成: 500–1000 条人工审核语料、训练依赖安装、tokenizer/checkpoint 下载、QLoRA、merge、GGUF 量化与 Ollama import。
- 恢复命令: `python -m venv .venv-finetune`；`.venv-finetune\Scripts\python -m pip install -r finetune/requirements-lock.txt`；`.venv-finetune\Scripts\python finetune/preflight.py`。
- GPU Gate: preflight 通过且 R10/数据/超参数冻结后，按 `finetune/README.md` 启动小模型 smoke，再决定 Qwen3-8B QLoRA。

## [2026-07-15 01:30] R12-GATE-AUDIT | 数据仍不足且无人审通过
- 类型: VERIFY / BLOCKED GATE
- 复验: `validate_dataset.py` 返回 53 samples / 53 valid / 0 failures；覆盖 17 visible tasks、8 families，其中 13 条带安全标签、26 条 correction、train/validation/internal-test=26/16/11。
- 审核状态: 53/53 均为 `draft`，0 条 `reviewed`；不能把结构校验或模型自审冒充人工审核。目标仍是 500–1000 条 reviewed，且安全/恢复不少于 20%。
- 环境: `environment_preflight.json` 仍为 `ready=false`，隔离训练环境缺 torch/transformers/trl/peft/accelerate/bitsandbytes/datasets。当前 14B R11 下载占用网络，未并发安装训练依赖。
- 决策: R10 controller 比较点已经冻结，但训练数据和超参数尚未冻结，R12 QLoRA 与 final blind 生成都不能启动。可继续生成基于 visible replay/captured observation 的 draft 候选；必须由人工审核后再过训练 gate。
