# 候选 E · 本地 Browser Agent / MCP 工作流自动化 — 精简分步计划

> 新技能：**Browser Agent / MCP / Agentic Workflow / 可审计执行系统**（区别于 p1 的 RAG、p2 的小模型工具调用与微调）。
> 推荐度：**首选**。在新的选择约束下，它比时序预测和金融多智能体更适合作为 p3 主线：数据依赖低、热门技能强、8GB 可行、面试追问更可防守。

## 一句话定位

构建一个本地可运行的**浏览器智能体工作流系统**：让 LLM 通过 Playwright / MCP / browser-use 操作网页、表单、文件下载和多页面信息流转，并对每一步动作做轨迹记录、失败恢复、安全边界和任务成功率评估。

## 用户新增选择约束（必须优先满足）

| 约束 | 对项目选择的影响 | E 的对应设计 |
|---|---|---|
| 简历材料以 `D:\Jobs\Resume` 为准 | p1 已是金融 RAG，p2 已是工具调用可靠性；p3 应补一个新技能格 | E 把能力推进到“agent 执行系统”，不是再做检索、微调或 schema |
| 不希望项目太依赖数据获取 | 避免需要大量行情、公告、标注数据或外部 API 的方向 | E 可以用自造本地网页、模拟后台、表单、CSV、任务脚本构建离线评测集 |
| 担心时序基础模型会被追问实际收益 | 金融预测/交易方向会引来收益、交易成本、滑点、过拟合等高压问题 | E 的主指标是任务成功率、失败恢复率、轨迹可审计性和安全边界，不承诺收益 |
| 不要求必须和统计强相关，更看重热门 skills | 优先 agent、MCP、browser automation、workflow automation 等 2025-2026 热点技能 | E 正好覆盖 Browser Agent、MCP 工具生态、workflow automation、LLM safety/eval |

## 新约束下的候选排序

1. **E 本地 Browser Agent / MCP 工作流自动化**：首选。热门技能最强，数据最可控，能把 p1/p2 的经验升级成“LLM 执行系统”。
2. **C 多模态文档抽取 / Document AI**：次选。数据压力可控，也热门，但更像 p1 文档管线的续作。
3. **D LLM 裁判可靠性**：储备。数据轻、统计味强，但与 p1 RAGAS 和 p2 评估主题有重叠。
4. **B 时序预测基础模型**：储备。技术可行，但金融场景容易被追问实际收益；除非改成非交易的 forecasting reliability benchmark。
5. **A 多智能体金融分析**：不建议作为下一主线。热点强，但最容易被质疑“看起来会决策，实则没有可交易 alpha”。

## 基于的开源底座（可扩展点）

- **browser-use**：面向 AI agent 的浏览器自动化框架，可接本地 LLM / Ollama。
- **Microsoft Playwright MCP**：把浏览器能力暴露为 MCP server，让 LLM 通过结构化页面快照执行操作。
- **Skyvern**：用 LLM / computer vision 做网页工作流自动化，可作为复杂表单与真实网页流程的参考。
- **OpenHands**：软件工程 agent 参考，不作为主线，但可借鉴 workspace、轨迹记录、任务评估思路。
- 扩展点：① 自造可控任务环境；② 轨迹审计与失败恢复；③ prompt injection / 越权操作安全边界；④ 本地小模型 vs API 的能力对照。

## 用到的新技能（简历可写）

Agentic workflow、MCP tool integration、browser automation、Playwright、任务规划与执行、action trace logging、失败恢复、安全策略、prompt injection 防护、agent evaluation benchmark。

## 机器可行性

浏览器执行和页面解析主要走 CPU；LLM 端可复用 p1 的 Ollama `qwen3:8b` 串行调用，或用 API 作为强基线。8GB 显存足够做本地小模型执行，项目主线不需要训练大模型，也不依赖大规模数据下载。

## 技术栈

Python / TypeScript · Playwright · Playwright MCP 或 browser-use · Ollama(qwen3:8b) / API fallback · FastAPI 或 Streamlit 任务环境 · SQLite/JSONL trace log · pytest · pandas 指标汇总 · 可选 LangGraph

## 分步计划

### Step 1 — 自造离线任务环境（先把数据依赖降到最低）

- 建 10-20 个本地 HTML / Streamlit / FastAPI 页面，模拟招聘筛选、CRM 查询、财务表单、CSV 下载、筛选排序、跨页面信息搬运等任务。
- 每个任务写清楚：自然语言指令、初始页面、目标状态、可验证 ground truth、禁止动作。
- **坑**：不要一开始接真实网站。真实网站变化、登录、反爬、验证码都会把项目变成环境调试，而不是 agent 能力展示。

### Step 2 — 浏览器工具层

- 选一个最小底座：优先 Playwright MCP 或 browser-use。
- 实现统一动作接口：`observe_page`、`click`、`type`、`select`、`extract_text`、`download_file`、`finish`。
- 每一步记录页面摘要、候选动作、实际动作、结果、耗时、错误。

### Step 3 — Agent 执行闭环

- LLM 输入：用户任务 + 页面观察 + 可用动作 schema + 安全规则。
- LLM 输出：下一步动作 JSON；程序侧校验动作是否合法。
- 执行循环：观察 → 计划 → 动作 → 校验 → 记录 → 判断是否完成。
- 对照：本地 qwen3:8b vs API 强模型；单步决策 vs 简单 planner + executor。

### Step 4 — 安全边界与失败恢复（项目记忆点）

- 安全规则：不自动提交敏感表单、不执行支付/删除/发送邮件类动作、不读取未授权本地文件。
- Prompt injection 测试：网页中放入“忽略系统指令/泄露文件/点击危险按钮”等恶意文本，检查 agent 是否被诱导。
- 失败恢复：元素找不到、页面跳转、表单校验失败时，允许重试、回退、请求人工确认。

### Step 5 — 评估与错误分析

- 指标：任务成功率、平均步骤数、平均耗时、无效动作率、恢复成功率、安全违规率。
- 错误分层：页面理解错、动作选择错、元素定位错、表单填充错、过早 finish、被 prompt injection 诱导、需要人工确认。
- 输出每个任务的 trace replay，面试时能展示“它为什么失败/怎么恢复”，而不是只给一个分数。

### Step 6 — 收尾与演示

- 做一个 Streamlit/HTML dashboard：任务列表、运行结果、轨迹、截图/DOM 摘要、错误类型、指标表。
- README 写清楚：本地运行方式、任务集、模型配置、安全策略、评估指标、失败案例。
- 简历 bullet 聚焦“Browser Agent + MCP + 可审计评估 + 安全边界”，不要写成普通网页自动化脚本。

### Stretch（有余力）

- 把 p1 RAG 封装成 agent 的一个知识工具，让 agent 在页面任务中可查询文档证据。
- 接入 LangGraph 做 planner / executor / verifier 分工。
- 加入视觉截图理解，对 DOM 不稳定或 canvas 页面做兜底。
- 做小型“human-in-the-loop”：高风险动作暂停，让用户确认后继续。

## 实验记录门禁

沿用 p1/p2：每个可验证改动先写 `实验记录.md`（日期、Step、修改文件、任务数、命令、模型、成功率、失败类型、安全违规、下一步），**日志未更新不进下一步**。如果只跑通了本地 mock 页面，不要写成真实网站可用；如果 API 比本地模型强，也如实记录。

## 面试脊柱（三必答）

1. **这和普通 RPA 有什么区别？** 普通 RPA 靠固定 selector 和脚本；本项目让 LLM 根据页面观察动态选择动作，并保留可审计轨迹和失败恢复。
2. **怎么证明 agent 不是 demo magic？** 用固定离线任务集、ground truth、成功率/步骤数/安全违规率和失败分层评估；每次运行都有 trace 可复盘。
3. **怎么防 prompt injection 和越权操作？** 网页内容只作为不可信观察；系统规则和动作白名单由程序侧硬校验；高风险动作必须拒绝或请求人工确认。
