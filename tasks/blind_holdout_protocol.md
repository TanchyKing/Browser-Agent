# Final Blind Holdout 封存协议

1. 先记录并提交 R10 controller commit、grader v2 digest、训练数据 manifest digest、超参数与 suite schema。
2. evaluator-only 执行者从四个任务族规范生成新值、新措辞、新 selector 和新布局；不得复制 development held-out 的实例。
3. 生成 `manifest.json`（task id、文件 SHA-256、grader expectation SHA-256），将任务正文与 expectation 分开加密/封存；Agent 工作区只获得 manifest 总哈希。
4. 在 `preregistration.json` 写明仅运行 R10 base 与 R12 fine-tuned、repeat 数、失败重试规则、主次指标和停止条件。
5. 两个模型全部完成后一次性解封评分；中途不查看逐任务结果。若基础设施故障，必须在看分数前记录作废原因并整体重跑。
6. 解封后只生成最终报告，不再修改 controller、grader、训练集或超参数。任何后续改动需建立新的 blind holdout。
