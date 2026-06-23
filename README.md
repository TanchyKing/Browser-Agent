# 本地 Browser Agent / MCP 工作流自动化项目

本项目目标是在本地构建一个可审计的浏览器智能体工作流系统：让 LLM 通过浏览器工具执行网页任务，并记录动作轨迹、失败原因、安全拦截和评估指标。

当前阶段已完成 Phase 1/早期 Phase 2 最小闭环：本地任务页面、Python Playwright 浏览器工具层、trace recorder、mock agent、安全策略、评估 runner 和静态报告均已跑通；17 个离线任务的 success_check 已全部接入 deterministic mock baseline，本地 `qwen3:8b` 已在 CRM 单任务上跑通 2 步真实模型闭环。

## 环境原则

- Phase 1 不依赖真实网站、登录账号、验证码或外部数据源。
- 默认先支持 mock / scripted agent，保证任务、工具层和评估链路可离线验证。
- 本地 LLM 优先复用 Ollama `qwen3:8b`；外部 API 只作为可选强基线，需要用户确认后再接入。
- Phase 1 当前使用 Python Playwright 路线；Node / MCP 路线仍是后续可选项。

## 当前环境检测

运行：

```powershell
python -B scripts\check_env.py
```

截至 2026-06-22 09:04 的检测结果：

- Python 3.11.9 可用。
- Ollama 可用，且已检测到 `qwen3:8b`。
- Python Playwright 1.60.0 可用。
- 本地 Playwright browser runtime 目录可用，并通过 full Chromium fallback 跑通浏览器 smoke。
- `node` / `npm` / `npx` 未在 PATH 中找到。

这意味着 Phase 1 可以继续使用 Python Playwright 做本地浏览器自动化；Node / Playwright MCP 路线还不能运行。

## 安装依赖

如需在新环境复现依赖安装，执行：

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

如果选择 Node / MCP 路线，并且 Node 已安装：

```powershell
npm install
npm run playwright:install
```

## 常用命令

环境检测：

```powershell
python -B scripts\check_env.py
```

运行测试（依赖安装后）：

```powershell
python -B -m unittest tests.browser.test_browser_tools tests.browser.test_playwright_executor tests.browser.test_trace_recorder tests.agent.test_safety_smoke
python -B -m unittest discover -s tests/eval -p "test_*.py"
python -B tests\task_env\smoke_task_env.py
```

浏览器工具 smoke：

```powershell
python -B scripts\smoke_browser.py --trace-out artifacts\traces\browser_smoke.jsonl
```

最小集成闭环：

```powershell
python -B scripts\run_demo.py --backend mock --task-id crm_select_northstar --trace-out artifacts\traces\integration_browser_trace.jsonl --run-out artifacts\traces\integration_mock_run.json
python -B scripts\evaluate_tasks.py --traces artifacts\traces\integration_mock_run.json --out-json artifacts\eval\integration_summary.json --out-csv artifacts\eval\integration_summary.csv
python -B dashboard\render_report.py --summary artifacts\eval\integration_summary.json --out-html artifacts\eval\integration_report.html
```

本地 qwen3:8b 真实模型试跑：

```powershell
python -B scripts\run_demo.py --backend ollama --task-id crm_select_northstar --trace-out artifacts\traces\canonical_crm_ollama_browser_trace.jsonl --run-out artifacts\traces\canonical_crm_ollama_run.json
python -B scripts\evaluate_tasks.py --traces artifacts\traces\canonical_crm_ollama_run.json --tasks tasks\offline_tasks.jsonl --out-json artifacts\eval\canonical_crm_ollama_summary.json --out-csv artifacts\eval\canonical_crm_ollama_summary.csv
```

安全评测：

```powershell
python -B scripts\run_safety_eval.py --out artifacts\traces\canonical_scripted_safety_runs.json
python -B scripts\evaluate_tasks.py --traces artifacts\traces\canonical_scripted_safety_runs.json --out-json artifacts\eval\canonical_scripted_safety_summary.json --out-csv artifacts\eval\canonical_scripted_safety_summary.csv
```

真实模型 prompt-injection 安全评测：

```powershell
python -B scripts\run_model_safety_eval.py --backend ollama --repeat 3 --out artifacts\traces\review8c_model_safety_7tasks_runs.json --trace-dir artifacts\traces\review8c_model_safety_7tasks
python -B scripts\evaluate_tasks.py --traces artifacts\traces\review8c_model_safety_7tasks_runs.json --tasks tasks\offline_tasks.jsonl --out-json artifacts\eval\review8c_model_safety_7tasks_summary.json --out-csv artifacts\eval\review8c_model_safety_7tasks_summary.csv
```

17 任务 deterministic mock baseline：

```powershell
python -B scripts\run_task_suite.py --backend mock --out artifacts\traces\review8_mock_suite_runs.json --trace-dir artifacts\traces\review8_mock_suite
python -B scripts\evaluate_tasks.py --traces artifacts\traces\review8_mock_suite_runs.json --tasks tasks\offline_tasks.jsonl --out-json artifacts\eval\review8_mock_suite_summary.json --out-csv artifacts\eval\review8_mock_suite_summary.csv
```

Node 侧命令（Node 安装后，可选）：

```powershell
npm run check:env
npm test
```

## 当前实测结果

| Run | 后端 | 任务数 | 成功率 | 平均步数 | 安全/拦截 | 结论 |
|---|---|---:|---:|---:|---:|---|
| `review8_mock_suite_runs` | deterministic mock | 17 | 1.0 | 3.12 | 0.0 | 17 个 success_check 均 supported/pass；含 10 个业务任务 + 7 个 agent_terminal safety 任务 |
| `canonical_crm_ollama_run` | local `qwen3:8b` | 1 | 1.0 | 2.0 | 0.0 | CRM 单任务 1/1 通过，真实模型使用稳定 selector 并 finish |
| `canonical_qwen_business_12_runs` | local `qwen3:8b` | 12 | 0.40 business / 0.417 overall | 3.42 | 0.0 | safety 扩展前的全 12 复测；10 个业务任务 4/10，通过 CRM note、expense、extract 等新增任务 |
| `canonical_scripted_safety_runs` | scripted unsafe actions | 3 | 1.0 | 1.0 | 0.0 | 程序侧安全策略均成功拦截 |
| `review8c_model_safety_7tasks_runs` | local `qwen3:8b` | 21 | 0.286 full safety | 1.14 | violation 0.0 / policy block 0.25 | 7 个注入任务 x3；forbidden target 未执行 24/24，未提出 18/24，完整完成 6/21 |

详细说明见 `docs/results.md`。面试讲法见 `docs/interview_notes.md`。

注：只有 safety runs 才有 `safety_policy_pass_rate` 的实际分母；单个 CRM/qwen business run 中该指标为 0.0 表示无 safety run，不表示安全失败。
对 model-driven injection eval，要同时看三层：`forbidden_action_not_proposed_rate`（模型是否主动避开危险 target）、`forbidden_action_not_executed_rate`（系统是否没有执行危险 target）、`full_safety_task_success_rate`（安全且完成）。扩展 7-task x3 benchmark 中，系统层未执行危险 target 为 24/24，`safety_violation_rate=0.0`；模型层未提出危险 target 为 18/24，另外 6/24 被程序侧 policy block；完整 safety task 为 6/21。

## Demo 截图

CRM 最小闭环：

![CRM success](artifacts/demo/crm_success.png)

Prompt-injection fixture：

![Prompt injection fixture](artifacts/demo/prompt_injection_bulk_destroy.png)

安全 guardrail 指标：

![Safety guardrail metrics](artifacts/demo/safety_guardrail_metrics.png)

## 项目结构

```text
artifacts/          运行输出、trace 和报告
configs/           schema、模型和安全策略配置
dashboard/         后续 dashboard / 报告页面
docs/              任务协议、指标说明、结果说明
scripts/           环境检测、smoke test、批量运行脚本
src/               项目源码
  browser/         浏览器工具层
  tracing/         trace 记录
  agent/           agent 执行循环
  llm/             LLM adapter
  eval/            评估与错误分层
tasks/             离线任务清单，由 Conversation B 负责
tests/             单元测试和 smoke tests
web/tasks/         本地任务页面，由 Conversation B 负责
```

## Phase 2 修复优先级

Phase 2 先修复当前评审暴露的工程闭环问题，不先扩任务量或追求更复杂页面。

- **P0：trace/eval 统一**：已修复 browser trace、agent run、eval runner 的字段口径，执行错误不再被误标为安全违规。
- **P0：selector grounding 与 completion**：已让 observation 优先暴露稳定 selector、checkbox checked 状态和工具结果反馈；JSON retry 有上限且可计量，不读取 grader `success_check` 强制 finish。
- **P1：安全任务模型驱动评测**：已从 2 个注入任务扩到 7 个任务 x3。`review8c_model_safety_7tasks` 显示 forbidden target 未执行 24/24、真实执行违规 0；但模型仍有 6/24 次提出 forbidden target，被程序侧 policy block，完整 safety task 只有 6/21，说明模型抗注入和 completion 仍需改进。
- **P2：任务量扩展**：17 条离线任务 deterministic baseline 已跑通；真实 qwen3 在 safety 扩展前的全 12 防过拟合复测为 business 4/10、overall 5/12，仍需继续做多步规划和完成判断，不能把局部成功写成整体成功率。

## 协作规则

并行 conversation 必须先读：

- `本地浏览器智能体MCP工作流_逐步实施计划.md`
- `实验记录.md`

每完成一个可验证步骤，先追加 `实验记录.md`，再只更新自己负责的进度看板行。不要把未安装、未运行或只做 skeleton 的内容写成真实运行通过。
