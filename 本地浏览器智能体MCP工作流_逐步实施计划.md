# 本地 Browser Agent / MCP 工作流自动化项目 · 逐步实施计划

> 目标：在 8GB 消费级 GPU 与有限数据获取渠道下，完成一个可运行、可评估、可演示的本地浏览器智能体工作流系统。核心不是做“会聊天的 agent”，而是做一个能操作网页、调用工具、记录轨迹、失败可恢复、边界可控的执行系统。

## 0. 角色标记

- **[Codex 可做]**：我可以直接在当前工作区完成，包括写代码、搭框架、生成本地任务页面、实现浏览器工具层、任务评估、trace dashboard、README 等。
- **[用户-only]**：只能由你完成或决定，包括最终项目方向确认、是否允许使用外部 API、是否安装需要管理员权限的软件、是否采用某个简历说法、是否接入真实账号/真实网站。
- **[共同]**：我可以先给默认实现或草案，你需要审阅、确认或调整，包括任务场景是否贴近求职目标、安全边界是否足够、是否保留某些 stretch。

## 0.1 并行对话的进度与实验记录规则

所有 conversation 都必须遵守以下规则：

1. **先读计划，再动手**：每次开始工作前先读 `本地浏览器智能体MCP工作流_逐步实施计划.md`，确认自己负责的边界。
2. **先查状态，再执行**：开始某个 step 前，先查看本文件的“0.2 进度看板”和 `实验记录.md`，避免重复做已经完成的工作。
3. **做完一步，先记录，再进入下一步**：每完成一个可验证 step，必须先更新 `实验记录.md`，再继续后续工作。
4. **计划里标注状态**：每完成一个 step，必须在“0.2 进度看板”里把对应状态从 `未开始` 或 `进行中` 改成 `已完成`，并写一句验证结果。
5. **实验记录必须可复现**：`实验记录.md` 至少写清楚时间、conversation、step、修改文件、运行命令、结果、失败/风险、下一步。
6. **阻塞也要记录**：如果因为缺依赖、缺浏览器运行时、缺 API key、网络、权限、用户确认、真实网站登录而暂停，也要在 `实验记录.md` 里写 `阻塞` 和需要谁处理。
7. **避免大范围改同一文件**：并行 conversation 更新本计划时，只改“0.2 进度看板”中自己负责的行；不要重排整份计划。
8. **不把未真实运行的结果写成已完成**：浏览器自动化、agent 执行、模型调用、安全测试、任务评估必须真实跑过，才能标记 `已完成`。

`实验记录.md` 是本项目的必需产物，不是可选文档。最后 README、简历 bullet、面试话术都必须从这里提取真实信息。

## 0.1.1 已冻结项目决策

1. **主线 topic**：本地 Browser Agent / MCP 工作流自动化。
2. **数据策略**：第一阶段不依赖真实网站和外部数据；用本地 HTML / FastAPI / Streamlit 任务环境自造离线评测集。
3. **面试定位**：不承诺投资收益，不做交易策略主线；指标聚焦任务成功率、失败恢复率、安全违规率、trace 可审计性。
4. **模型策略**：本地 `qwen3:8b` / Ollama 作为可选本地后端，API 只作为强基线或 stretch，不能成为唯一可运行依赖。
5. **安全策略**：高风险动作默认不自动执行；提交、删除、支付、发送邮件、读取未授权本地文件等动作必须拒绝或请求人工确认。
6. **第一阶段底座选择**：优先 Playwright 原生接口 + 可选 Playwright MCP/browser-use 适配；先跑通闭环，再决定是否深接某个开源框架。
7. **项目边界**：p1 RAG 可作为后续知识工具接入，但不是 Phase 1 必需；p2 的 schema/约束思想可复用，但不再做 LoRA 微调主线。

## 0.2 进度看板

状态只使用：`未开始`、`进行中`、`已完成`、`阻塞`、`需用户确认`。

| Conversation | Step | 任务 | 状态 | 最新验证/备注 |
|---|---|---|---|---|
| A | A.1 | 项目目录结构与基础配置 | 已完成 | 2026-06-22 00:47 验证核心目录与 `.gitkeep` 占位存在；仅创建空目录，未写业务逻辑或任务数据 |
| A | A.2 | Python/Node/Playwright 环境检测脚本 | 已完成 | 2026-06-22 09:04 复查：Python/Ollama/qwen3:8b、Python Playwright 1.60.0 与 browser runtime 可用；Node/npm/npx 仍缺 |
| A | A.3 | 依赖文件与开发命令 | 已完成 | 2026-06-22 00:50 新增 `requirements.txt`、`pyproject.toml`、`package.json`；静态解析通过，未安装依赖 |
| A | A.4 | README 环境小节与本地启动骨架 | 已完成 | 2026-06-22 00:51 README 环境/启动骨架已写入并读回验证；明确 Playwright/Node 未安装，未写结果结论 |
| A | A.5 | Phase 2 修复前置清理与仓库卫生 | 已完成 | 2026-06-22 10:51 旧 `落地计划.md` 已标记为被取代；新增 `.gitignore`；README 写入 Phase 2 P0 修复优先级；清理并复查无 `__pycache__`/`*.pyc` |
| B | B.1 | 离线任务协议与 JSON Schema | 已完成 | 2026-06-22 10:54 已与 action schema 对齐：`request_human` 替代 `ask_user`，新增 `agent_terminal`/`support_status`；JSON 解析通过 |
| B | B.2 | 本地任务页面原型 | 已完成 | 2026-06-22 10:54 13 个本地 HTML 页面已补 `data-testid` 与行级标识，减少多匹配 selector 风险 |
| B | B.3 | 任务清单与 ground truth | 已完成 | 2026-06-22 21:05 `tasks/offline_tasks.jsonl` 扩到 17 条任务；新增 5 个 prompt-injection 变体，总计 7 个 safety tasks，所有 success_check 均为 current_eval |
| B | B.4 | 任务环境 smoke test | 已完成 | 2026-06-22 21:05 增强 smoke 通过：17 tasks / 8 categories / 7 safety tasks；所有 success_check 均为 current_eval |
| C | C.1 | 浏览器工具层接口 | 已完成 | 2026-06-22 10:56 `BrowserActionResult` 增加结构化 `error_type`；browser 单测 9 个通过（1 skipped） |
| C | C.2 | Playwright 执行器 skeleton | 已完成 | 2026-06-22 10:56 observation 元素输出稳定可执行 `selector`，优先 data-testid/id/name，fallback `tag >> nth=N`；已移除 `click(force=True)` |
| C | C.3 | Trace 记录基础结构 | 已完成 | 2026-06-22 10:56 Trace JSONL 改为 0-based step_index，并包含 run_id/action/ok/error_type/error/observation 摘要/elapsed_ms |
| C | C.4 | 浏览器工具 smoke test | 已完成 | 2026-06-22 10:56 真实 Playwright smoke 通过；`artifacts\traces\browser_smoke.jsonl` 4 步 trace 索引为 `[0,1,2,3]` |
| D | D.1 | Agent action schema 与安全策略 | 已完成 | 2026-06-22 00:50 `python -B -m py_compile src\agent\actions.py src\agent\safety.py` 通过；已定义 action schema 与程序侧安全策略 |
| D | D.2 | LLM adapter skeleton | 已完成 | 2026-06-22 00:52 mock adapter import 与 JSON 解析通过；Ollama 标准库 HTTP 接口仅预留，未调用真实模型 |
| D | D.3 | Agent 执行循环 skeleton | 已完成 | 2026-06-22 19:15 已补 JSON retry 与 completion feedback：首次/重试后 JSON 合法率可计量；extract/download 工具结果、重复动作和 recoverable browser error 会回喂 observation；仍不读取 grader `success_check` 强制 finish |
| D | D.4 | 安全拦截 smoke test | 已完成 | 2026-06-22 21:05 `review8c_model_safety_7tasks` 重算后 forbidden target 未执行 24/24、policy_block_rate=0.25、safety_violation_rate=0.0；程序侧 guardrail 拦住 6/24 forbidden proposals |
| E | E.1 | 评估指标与结果格式 | 已完成 | 2026-06-22 10:58 P0 修复：拆分 business task success 与 safety policy pass，新增 browser_execution_error_rate；E 线 unittest 17/17 通过 |
| E | E.2 | 任务评估 runner | 已完成 | 2026-06-22 10:58 P0 修复：runner 可消费 run artifact、C 线 browser JSONL step trace，并自动/显式合并 `artifacts.browser_trace` |
| E | E.3 | 错误分层与 trace replay | 已完成 | 2026-06-22 16:00 P0 复核修复：执行错误 `error_type` 已从 browser/runner/run artifact/eval 打通；旧 qwen 失败重评不再误标 `forbidden_action`，新 qwen CRM run error_counts 为空 |
| E | E.4 | Dashboard/报告骨架 | 已完成 | 2026-06-22 10:58 P0 修复：report 区分 mock/model_driven/scripted_safety，scripted safety 显示 policy-unit warning，success_check 支持性汇总可见 |
| F | F.1 | 集成最小闭环 | 已完成 | 2026-06-22 09:07 本地 CRM 任务 + Playwright + mock agent + 安全策略 + 评估/report 跑通；1 run success，task_success_rate=1.0 |
| F | F.2 | 本地 qwen3:8b 首轮试跑 | 已完成 | 2026-06-23 00:15 首轮负结果已完成复核与修复；展示版证据已复制为 `canonical_crm_ollama_run.json`，显示 qwen3:8b 在 CRM 任务 2 步成功 |
| F | F.5 | 17-task mock baseline + qwen full-suite subset | 已完成 | 2026-06-22 21:05 mock baseline 已扩到 17/17 通过；qwen safety 扩展前全 12 复测为 overall 5/12、business 4/10，失败集中在 planner/completion/JSON |
| F | F.6 | Model-driven prompt injection eval | 已完成 | 2026-06-22 21:05 qwen3 7 个 safety tasks x3 复测：forbidden target 未执行 24/24、未提出 18/24、完整 safety completion 6/21；6/24 forbidden proposals 被 policy block，真实执行违规 0 |
| F | F.3 | 安全与 prompt injection 小评测 | 已完成 | 2026-06-22 09:14 3 个真实浏览器安全场景均被程序侧拦截；safety_violation_rate=0.0 |
| F | F.4 | README、简历 bullet、面试问答 | 已完成 | 2026-06-22 21:05 README、`docs/results.md`、`docs/interview_notes.md` 已按 17-task baseline 与 7-task safety eval 更新；未写入正式简历 |

## 1. 项目前置条件

### 1.1 硬件与系统

| 前置项 | 状态/要求 | 负责人 |
|---|---|---|
| GPU | RTX 5070 Laptop 8GB；本项目不依赖训练大模型 | [用户-only] 保持可用即可 |
| 内存 | 32GB，足够浏览器任务、trace、评估 | [Codex 可做] 检查 |
| Python | Python 3.11 优先 | [Codex 可做] 检查 |
| Node/浏览器 | Playwright 可能需要 Node 和浏览器运行时 | [Codex 可做] 检查；安装异常时 [用户-only] 处理权限/网络 |
| Ollama | 可选本地 LLM 后端，优先复用 p1 的 qwen3:8b | [Codex 可做] 检查；模型缺失时 [用户-only] 决定是否下载/切 API |

### 1.2 依赖原则

| 原则 | 说明 |
|---|---|
| 轻依赖优先 | 先用 Playwright + Python 标准工具跑通，不急着引入大型 agent 框架 |
| mock 优先 | LLM 后端先支持 mock，保证任务环境、工具层、评估层可离线验证 |
| API 可选 | API 只能作为强基线，不作为项目唯一运行路径 |
| 真实网站后置 | Phase 1 禁止依赖登录、验证码、反爬或真实账号 |

### 1.3 需要用户确认的事项

| 决策 | 默认建议 | 负责人 |
|---|---|---|
| 是否允许使用外部 API 做强基线 | 默认不需要，先本地/mock | [用户-only] |
| 是否接真实网站 | Phase 1 不接；Phase 3 可选接一个无登录公开站点 | [用户-only] |
| 任务场景偏向 | 默认通用办公/CRM/招聘/财务表单，不绑定金融收益 | [共同] |
| 简历是否突出 MCP | 默认突出 Browser Agent + MCP-ready，不夸大为完整 MCP 产品 | [共同] |

## 2. 并行工作流总览

| 工作流 | 可并行吗 | 主要产物 | 负责人 |
|---|---:|---|---|
| A. 项目脚手架与环境 | 是 | 目录结构、依赖、环境检测、README 环境小节 | [Codex 可做] |
| B. 本地任务环境与数据协议 | 是 | 任务 schema、本地页面、任务清单、ground truth | [Codex 可做] + [共同] |
| C. 浏览器工具层与 trace | 是 | Playwright 执行器、工具接口、trace 记录 | [Codex 可做] |
| D. Agent 循环与安全策略 | 是 | action schema、LLM adapter、执行循环、安全拦截 | [Codex 可做] |
| E. 评估、错误分析与 dashboard | 是 | 指标、runner、错误分层、报告骨架 | [Codex 可做] |
| F. 集成、真实模型试跑与交付 | 依赖 A-E 最小版本 | 集成闭环、qwen3 试跑、安全评测、README/简历 | [Codex 可做] + [共同] |

## 3. 详细步骤与依赖

### Phase 0：启动准备

| Step | 任务 | 依赖 | 可否并行 | 负责人 |
|---|---|---|---:|---|
| 0.1 | 创建项目目录结构 | 无 | 是 | [Codex 可做] |
| 0.2 | 创建实验记录与进度规则 | 无 | 否 | [Codex 可做] |
| 0.3 | 检查 Python/Node/Playwright/Ollama | 无 | 是 | [Codex 可做] |
| 0.4 | 决定是否允许外部 API | 无 | 是 | [用户-only] |

### Phase 1：最小可运行版本

| Step | 任务 | 依赖 | 可否并行 | 负责人 |
|---|---|---|---:|---|
| 1.1 | 定义任务协议和 action schema | 无 | 是 | [Codex 可做] |
| 1.2 | 生成 10-20 个本地任务页面 | 1.1 初稿 | 是 | [Codex 可做] |
| 1.3 | 写任务清单与 ground truth | 1.1 | 是 | [Codex 可做]，[共同] 抽查任务合理性 |
| 1.4 | 实现 Playwright 工具层 | A.3 | 是 | [Codex 可做] |
| 1.5 | 实现 trace 记录 | 1.4 | 是 | [Codex 可做] |
| 1.6 | 实现 mock LLM adapter | D.1 | 是 | [Codex 可做] |
| 1.7 | 实现 agent 执行循环 | C.1、D.1、D.2 | 部分并行 | [Codex 可做] |
| 1.8 | 实现评估 runner | B.3、C.3 | 是 | [Codex 可做] |
| 1.9 | 跑通一个 scripted/mock agent 任务 | B/C/D/E 最小版本 | 否 | [Codex 可做] |

Phase 1 完成标准：
- 有可解析的任务集。
- 有可打开的本地任务页面。
- 有浏览器工具层和 trace。
- 有 mock/scripted agent 能完成至少一个任务。
- 有评估 runner 输出成功/失败与 trace 文件。

### Phase 2：Agent 能力与安全评测

| Step | 任务 | 依赖 | 可否并行 | 负责人 |
|---|---|---|---:|---|
| 2.1 | 接入 Ollama qwen3:8b 或记录阻塞 | Phase 1 | 否 | [Codex 可做]，[用户-only] 保证模型可用 |
| 2.2 | 加入 prompt injection 任务 | B.3 | 是 | [Codex 可做] |
| 2.3 | 加入 forbidden action 程序侧拦截 | D.1 | 是 | [Codex 可做] |
| 2.4 | 加入失败恢复策略 | C/D 最小版本 | 是 | [Codex 可做] |
| 2.5 | 批量评估本地模型 vs mock/scripted baseline | 2.1-2.4 | 否 | [Codex 可做] |
| 2.6 | 错误分层与 trace replay | 2.5 输出 | 否 | [Codex 可做] |

Phase 2 完成标准：
- 至少 10 个任务可批量运行。
- 本地模型或明确记录的可替代后端有首轮结果。
- 安全拦截经过真实测试。
- 有任务成功率、步骤数、安全违规率、错误类型汇总。

### Phase 3：演示与交付

| Step | 任务 | 依赖 | 可否并行 | 负责人 |
|---|---|---|---:|---|
| 3.1 | Dashboard 展示任务、trace、指标 | Phase 2 输出 | 是 | [Codex 可做] |
| 3.2 | README 与复现实验命令 | Phase 2 输出 | 是 | [Codex 可做] |
| 3.3 | 简历 bullet 与面试问答 | Phase 2 输出 | 否 | [共同] |
| 3.4 | 可选接入 p1 RAG 作为知识工具 | Phase 1 稳定 | 是 | [Codex 可做]，[用户-only] 确认是否值得做 |
| 3.5 | 可选接入真实公开网页 | Phase 2 稳定 | 否 | [用户-only] 确认目标站点 |

## 4. 你必须亲自完成/确认的事项

这些事情我不能替你“假装完成”：

1. **最终是否采用 E 作为 p3 主线**：目前计划按 E 推进。
2. **是否允许使用外部 API**：默认不使用；若要做强基线，需要你确认 key/费用/隐私边界。
3. **是否接真实网站或真实账号**：默认不接；涉及账号、登录、验证码、隐私数据必须你确认。
4. **任务场景是否贴近你的求职叙事**：我可以做通用办公/CRM/招聘/财务表单，你需要判断是否合适。
5. **最终简历是否采用某个说法**：必须基于真实跑过的实验结果。

## 5. 我可以直接完成的事项

我可以在工作区内直接推进：

1. 搭建项目目录结构。
2. 写 `requirements.txt` / `pyproject.toml` / 可选 `package.json`。
3. 写环境检测脚本。
4. 写任务 JSON Schema 与 action JSON Schema。
5. 生成本地 HTML/FastAPI/Streamlit 任务页面。
6. 写任务清单和 ground truth。
7. 写 Playwright 浏览器工具层。
8. 写 trace recorder。
9. 写 mock/Ollama/API LLM adapter。
10. 写 agent 执行循环。
11. 写安全策略与动作拦截。
12. 写评估 runner 和错误分层。
13. 写 dashboard/report。
14. 写 README、实验记录模板、简历 bullet 草案。

## 6. 推荐并行 Conversations

建议开 5 个并行对话，每个对话只负责一个清晰工作流，避免互相踩文件。

### Conversation A：项目脚手架与环境

任务：
- 创建项目目录结构。
- 写依赖文件。
- 写环境检测脚本。
- 写 README 环境小节。

建议提示词：

```text
你负责 D:\Study\Projects\p3 的“本地 Browser Agent / MCP 工作流自动化项目”的项目脚手架与环境工作流。
请先阅读 本地浏览器智能体MCP工作流_逐步实施计划.md 的 0.1/0.2 和 实验记录.md，只处理项目结构、依赖文件、环境检测脚本、README 环境小节。
不要改任务数据、浏览器执行逻辑、agent 逻辑或评估逻辑。
完成每个可验证步骤后，先追加 实验记录.md，再只更新本计划 0.2 进度看板中 Conversation A 的对应行。
```

### Conversation B：本地任务环境与数据协议

任务：
- 设计任务协议和 JSON Schema。
- 生成本地任务页面。
- 写任务清单与 ground truth。
- 写任务环境 smoke test。

建议提示词：

```text
你负责 D:\Study\Projects\p3 的“本地 Browser Agent / MCP 工作流自动化项目”的本地任务环境与数据协议工作流。
请先阅读 本地浏览器智能体MCP工作流_逐步实施计划.md 的 0.1/0.2 和 实验记录.md，只处理 configs/schema/、docs/task_spec.md、tasks/、web/tasks/、tests/task_env/。
任务环境必须不依赖真实网站和外部数据；每个任务都要有可程序判定的 expected_state 和 forbidden_actions。
完成每个可验证步骤后，先追加 实验记录.md，再只更新本计划 0.2 进度看板中 Conversation B 的对应行。
```

### Conversation C：浏览器工具层与 Trace

任务：
- 写浏览器工具接口。
- 写 Playwright 执行器 skeleton。
- 写 trace recorder。
- 用脚本式动作完成一个简单本地任务。

建议提示词：

```text
你负责 D:\Study\Projects\p3 的“本地 Browser Agent / MCP 工作流自动化项目”的浏览器工具层与 trace 工作流。
请先阅读 本地浏览器智能体MCP工作流_逐步实施计划.md 的 0.1/0.2 和 实验记录.md，只处理 src/browser/、src/tracing/、scripts/smoke_browser.py、tests/browser/。
不要改任务 schema，不要写 LLM agent 决策逻辑；需要任务页面时可使用 B 已生成的任务或先做最小本地 fixture。
完成每个可验证步骤后，先追加 实验记录.md，再只更新本计划 0.2 进度看板中 Conversation C 的对应行。
```

### Conversation D：Agent 循环与安全策略

任务：
- 写 action schema。
- 写 LLM adapter skeleton（mock/Ollama/API）。
- 写 agent 执行循环。
- 写安全拦截 smoke test。

建议提示词：

```text
你负责 D:\Study\Projects\p3 的“本地 Browser Agent / MCP 工作流自动化项目”的 agent 循环与安全策略工作流。
请先阅读 本地浏览器智能体MCP工作流_逐步实施计划.md 的 0.1/0.2 和 实验记录.md，只处理 configs/safety_policy.yaml、configs/schema/action.schema.json、src/agent/、src/llm/、tests/agent/。
默认先用 mock LLM，不依赖外部 API；高风险动作必须由程序侧拦截或要求人工确认。
完成每个可验证步骤后，先追加 实验记录.md，再只更新本计划 0.2 进度看板中 Conversation D 的对应行。
```

### Conversation E：评估、错误分析与 Dashboard

任务：
- 写指标定义。
- 写批量评估 runner。
- 写错误分层。
- 写 dashboard/report 骨架。

建议提示词：

```text
你负责 D:\Study\Projects\p3 的“本地 Browser Agent / MCP 工作流自动化项目”的评估、错误分析与 dashboard 工作流。
请先阅读 本地浏览器智能体MCP工作流_逐步实施计划.md 的 0.1/0.2 和 实验记录.md，只处理 src/eval/、scripts/evaluate_tasks.py、docs/metrics.md、dashboard/、tests/eval/。
评估必须区分任务成功、动作有效性、失败恢复、安全违规和错误类型；没有真实 agent 输出时先支持 mock trace。
完成每个可验证步骤后，先追加 实验记录.md，再只更新本计划 0.2 进度看板中 Conversation E 的对应行。
```

## 7. 并行执行时的文件边界

| Conversation | 主要可编辑路径 | 避免编辑 |
|---|---|---|
| A 环境脚手架 | `requirements.txt`、`pyproject.toml`、`package.json`、`scripts/check_env.py`、`README.md` 环境部分 | `tasks/`、`src/agent/`、`src/eval/` |
| B 任务环境 | `configs/schema/task.schema.json`、`docs/task_spec.md`、`tasks/`、`web/tasks/`、`tests/task_env/` | `src/browser/`、`src/agent/`、`src/eval/` |
| C 浏览器工具 | `src/browser/`、`src/tracing/`、`scripts/smoke_browser.py`、`tests/browser/` | 任务 schema、LLM adapter、评估指标 |
| D Agent 安全 | `configs/schema/action.schema.json`、`configs/safety_policy.yaml`、`src/agent/`、`src/llm/`、`tests/agent/` | 任务页面、浏览器底层、eval runner |
| E 评估报告 | `src/eval/`、`scripts/evaluate_tasks.py`、`docs/metrics.md`、`dashboard/`、`tests/eval/` | agent/browser 实现、任务页面 |
| F 集成交付 | `README.md`、`docs/results.md`、`docs/interview_notes.md`、`scripts/run_demo.py` | 未经确认不要重写 A-E 的核心实现 |

## 8. 第一周建议排程

| Day | 用户 | Codex/并行 conversations |
|---|---|---|
| Day 1 | 确认 E 为主线；决定是否允许 API 强基线 | A 建环境；B 写任务协议；C/D/E 写 skeleton |
| Day 2 | 抽查任务场景是否合适 | B 生成 10-20 个本地任务；C 浏览器工具 smoke；D safety smoke |
| Day 3 | 确认是否接 Ollama qwen3:8b | F 集成 mock/scripted agent 最小闭环；E 出第一版指标 |
| Day 4 | 看失败案例，决定是否调任务难度 | D 接 Ollama；C/E 完善 trace 和错误分层 |
| Day 5 | 决定是否加入 p1 RAG 工具或 API 强基线 | 批量评估 + dashboard |
| Day 6 | 审阅 README 和简历 bullet | 安全测试、prompt injection 小评测 |
| Day 7 | 决定是否发布为 GitHub 项目 | 收尾文档、面试问答、可复现命令 |

## 9. 立即可执行的下一步

最优顺序：

1. 创建并行 Conversation A-E。
2. Conversation A 先搭项目结构和环境检测。
3. Conversation B 起草任务协议与本地任务环境。
4. Conversation C/D/E 同步做浏览器工具、agent 安全、评估 skeleton。
5. 等 A-E 都有最小骨架后，由 F 或主对话做第一次集成。
6. 若需要外部 API、真实网站、账号登录、或决定任务场景是否贴近求职叙事，则暂停并请求用户确认。

第一阶段不要急着接真实网站。先让本地任务、工具层、agent loop、trace、evaluation 全部跑通，后面的 MCP/browser-use/Skyvern 接入才不会变成黑箱试错。
