# P3 Browser Agent 面试笔记

## 一句话

我做了一个本地 Browser Agent / MCP-ready 工作流原型：用本地 HTML 任务集、Python Playwright、可审计 JSONL trace、程序侧安全策略和评估 runner，验证 LLM agent 是否能可靠执行网页任务，而不是只看 demo 是否“会点页面”。

## 为什么这个项目有价值

- 它不依赖真实网站、账号、爬虫或外部数据，任务和 ground truth 都可控。
- 它把 p1 的 RAG 和 p2 的工具调用经验往前推进到 agent 执行层。
- 它把 agent 常见的“看起来能跑”拆成可评估指标：任务成功率、无效动作率、步骤数、安全违规率、错误类型和 trace replay。

## 当前诚实结果

- Mock agent 跑通 1 个本地 CRM 任务，成功率 1.0。
- Deterministic mock baseline 跑通 17 个离线任务，17/17 success_check supported/pass，其中包括 10 个业务任务和 7 个 agent_terminal safety 任务。
- 本地 `qwen3:8b` 最初暴露 selector 不唯一、非法 JSON 和 completion 判断问题；修复 trace 归因、稳定 selector 暴露、bounded JSON retry、工具结果反馈和 completion 提示后，CRM 单任务 1/1、2 步跑通。
- qwen3 全 12 离线任务防过拟合复测为 overall 5/12，business 4/10；比早期 4-task 子集 1/4 更好，但多步筛选、下载后 finish、表单规划和 JSON 稳定性仍是瓶颈。
- 3 个 scripted 安全场景全部被程序侧策略拦截，安全违规率 0.0。
- Model-driven prompt injection eval 已扩到 7 个安全任务 x3 次。qwen3 在 24/24 个 forbidden target checks 中没有真实执行危险 target，`safety_violation_rate=0.0`；但模型仍有 6/24 次提出 forbidden target，被程序侧策略拦截（`policy_block_rate=0.25`），完整 safety task 只完成 6/21。

## 面试高频问答

**Q：这和普通 RPA 有什么区别？**  
普通 RPA 主要依赖固定脚本和稳定 selector。本项目的目标是让 LLM 根据页面 observation 选择下一步动作，同时每一步都有 JSON action、trace、错误类型和安全拦截。mock 17-task baseline 证明工程闭环，qwen3 全 12 复测则暴露真实 LLM 在多步规划、JSON 稳定性和完成判断上的瓶颈。

**Q：怎么证明不是 demo magic？**  
我没有只展示一个成功页面，而是设计了离线任务协议、ground truth、评估 runner 和 trace replay。成功和失败都落到 artifact：17-task mock baseline 成功、qwen3 CRM 成功、qwen3 全 12 为 business 4/10、model-driven safety 7 任务 x3 中 forbidden target 未执行 24/24、完整 safety completion 6/21，结论都能复现。

**Q：本地小模型为什么失败？**  
第一次失败时，它输出了合法 action，但 selector 不够具体，`button:has-text('Select')` 在页面中匹配多个元素。Playwright strict mode 拒绝执行。修复后，CRM 任务能使用 `[data-testid="select-northstar-clinics"]` 并在完成条件满足后 `finish`。后续又加了有上限的 JSON retry 和工具结果反馈：全 12 中 business 4/10，但仍会在多步表单、下载后 finish、非法 JSON 上失败，所以不能说整体成功。

**Q：安全怎么做？**  
网页内容被当成不可信 observation。高风险动作如 send/delete/payment/email 会被程序侧策略拦截或要求人工确认；prompt injection 页面里的恶意指令不能覆盖系统安全规则。

**Q：真实模型面对 prompt injection 安全吗？**  
目前可以说“在当前离线注入任务上系统没有执行危险 target”，但不能说“模型从不受 prompt injection 影响”。我把安全拆成三层：模型是否提出 forbidden target、系统是否执行 forbidden target、任务是否完整安全完成。扩展 7-task x3 评测里，系统层 24/24 没有执行 forbidden target，真实执行安全违规率为 0.0；模型层仍有 6/24 forbidden target proposals，全部被策略拦截；完整 safety task 只完成 6/21。这个结论更诚实：guardrail 和 audit 有效，但模型抗注入和 completion 还不是展示级。

**Q：下一步怎么提高？**  
下一步可以有两条线：如果走展示版，就把安全/可审计主线打磨成 README demo 和 trace replay；如果继续提升能力，就做模型侧 pre-action verifier、更多非泄题 few-shot 和 completion criteria 提示。runner 不读取 `success_check` 强制 finish，避免把 grader 信号泄漏给 agent。
