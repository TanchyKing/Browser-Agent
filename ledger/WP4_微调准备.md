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

## [2026-07-15 12:52] AUTORUN-DATA-GROUNDING-CORRECTION | safe-brief 合同此前不可达
- 类型: FAILURE / CORRECTION / IMPLEMENTATION
- 发现: R10d/e/f public contract 要求 `extract_text` 命中 `safe-brief`，但 browser observation 只暴露 a/button/input/select/textarea；实际 `<p data-testid="safe-brief">` 不在 candidate snapshot。Prompt 又要求只能使用观察中出现的 selector，因此真实模型只能反复提取 `safe-summary` 按钮文字。
- 历史边界: 已冻结 R10d/e/f artifacts 与分数不修改、不重跑；此问题解释其 safety evidence failure，但不事后改变实验。旧 53-row seed 经增强 grounding validator 重验为 42 valid / 11 ungrounded，保留审计但禁止训练。
- 修复: observation 新增所有可见 `[data-testid]` 节点，使 read-only p/div/status 具备真实可执行 selector；隐藏节点仍过滤。它是 Agent 可见 DOM，不读取 grader success-check。
- 验证: Playwright test 证明 `safe-brief` 出现在 observation/candidate；R10e mock delete 真实提取 `14 active records remain unchanged` 并 finish success。Legacy 与 R10e mock 均 17/17。

## [2026-07-15 13:11] AUTORUN-STAGE3-COMPLETE | 588 条 grounded draft 与逐行审核队列
- 类型: DATA BUILD / VERIFY / HANDOFF
- 数据: `visible_step_drafts_split.jsonl` 共 588 unique samples；business 458、safety/recovery 130（22.11%）；actions 包含 click 94、download 2、extract 64、finish 148、request-human 10、select 98、type 172。
- 来源/覆盖: 只重放 17 个 visible 本地 fixture；包含多字段动作顺序、target/value 顶层纠错、generic finish 纠错、safe-brief 提取与具体事实携带、policy alternative 和 multiple-action JSON correction。Development/final blind 零引用，无隐藏 CoT。
- Split: train 486、validation 68、internal-test 34；业务 trajectory ordering 与安全 recovery context 作为不可拆模板，template split leak=0。安全在 train/validation/internal 分别 104/18/8。
- 校验: full Draft 2020-12 schema + unique id + target grounding + holdout exclusion 588/588；绝对 workspace path 0；第二次独立 build 的 dataset/queue SHA 完全一致。Dataset SHA-256=`EEAFE541...3397967`，manifest 固定完整哈希。
- 审核: `review_queue.csv` 588 行，decision 全空；dataset 588/588=`draft`、0 reviewed。新增 `REVIEW_QUEUE_GUIDE.md` 与安全的独立输出脚本，只有明确人工 approve 才能在新文件中标 reviewed。
- 回归: pytest collected 130，129 passed/1 environment skip；legacy mock 17/17，R10e mock 17/17。
- Gate: 数量门槛已达到，但人工门禁完全未通过；不得启动 QLoRA、不得准备训练用 reviewed SFT、不得生成或运行 final blind。

## [2026-07-16 00:26] SEMANTIC-DUAL-RENDER | 588 条单次人审语义层与双接口渲染
- 类型: DATA SCHEMA / IMPLEMENTATION / VERIFY / CORRECTION
- 口径: 当前唯一审核/训练候选仍是 588 条；历史 53-row seed 不合并。588 条中 terminal=158，不再使用两文件 641/175 的错误口径。
- 语义层: 每条新增 `semantic_completion.action_reason`；terminal 另含 `user_visible_result`。canonical completion 保持 R10e 视图，validator 强制 terminal reason 与审核事实一致，防止界面序列化漂移。
- 双渲染: `prepare_sft.py --interface r10e` 把审核事实写入 reason；`--interface r10f` 写入独立 answer 并同步切换 terminal-answer tools schema。全 588 条两种渲染均通过 schema，R10e terminal answer=0/158，R10f=158/158，非终端 answer=0。
- Observation 依赖: corpus 以 R10g `visible_testids` 真实 Playwright replay 重建，与冻结 R10d/e/f observation 不一致；manifest 和 DATASET_CARD 已显式标注。
- 数据: 仍为 588 draft/0 reviewed，business 458、safety/recovery 130、split 486/68/34；新 dataset SHA-256=`9A53228670AB8836582E8D79E8551988AE16080FA02A9C3A26BDCAD7C4C66161`，queue SHA-256=`0F6D4F1CB150869AA7E4E14467E0E3E44C052BE96E57C89C338AA860E0994977`；两次独立生成完全一致。
- 审核: review queue 新增只读 action/semantic 两列，decision 仍 588/588 空白。渲染不产生 reviewed 状态，不替代人工判断。
- 边界: 未准备正式 SFT reviewed 文件、未安装训练栈、未训练、未读取 heldout/blind 数据。

## [2026-07-16 08:20] REVIEW-COMPLETE | 588 条语料委托审核完成
- 类型: VERIFY / DECISION
- 审核者: claude-fable-5（本项目独立审核方，与语料生成方 Codex 相互独立）。用户于 2026-07-16 在会话中明确委托其代行人工 Gate；这是**委托 AI 审核**而非项目所有者亲自审核，所有者保留抽查与撤销权。
- 方法: REVIEW_QUEUE_GUIDE 六项标准全部程序化执行于 588/588 行（target/option grounding、合同泄漏扫描、terminal 事实 grounding、forbidden target 扫描、type/select 值一致性 270/270、模板拆分完整性 0 泄漏），另按 71 个 (task, action, correction, safety) 分层做全样本人工判读，并逐条核对 17 个唯一 terminal 结果与 fixture 事实一致。
- 结论: 588/588 approve；`apply_review_queue.py` 产出 `finetune/data/reviewed/visible_step_reviewed.jsonl`，`validate_dataset.py` 复验 valid 588/588、0 泄漏。
- 随批记录的语料级发现（详见 DATASET_CARD Review record）: ①槽位值零多样性（记忆风险，二轮训练前建议值变体扩充）；②60 条 benefits 行 family 误标为 invoice_form（仅元数据）；③注入变体仅措辞变化，布局泛化仍由 heldout/blind 负责。
- 验证命令: python -B finetune/validate_dataset.py --input finetune/data/reviewed/visible_step_reviewed.jsonl → {"valid": 588, "failures": []}
- 下一步: 训练线按 WP5 GATE-AUTHORIZATION 推进。
