# v2.0 第一版评测骨架

这里保存 GLEN LST Agent 的黄金用例、Agent 轨迹和程序化评测器。v2.0 已包含 v1.0 的完整项目副本；评测代码只读被测项目，不修改业务数据。

## 快速运行

```powershell
python evals/run_eval.py `
  --cases evals/cases/golden.jsonl `
  --traces evals/traces/sample.jsonl `
  --output evals/reports/sample.json
```

`sample.jsonl` 只有少量示例轨迹，因此会报告缺失用例。真实评测时，将 Agent 运行轨迹按同样格式写入 `evals/traces/latest.jsonl`。

## 下一步接入

1. 在 `app/agent.js` 记录每次 LLM 请求和工具调用。
2. 让真实 Agent 运行结果写入 `evals/traces/latest.jsonl`。
3. 将 SQL、RF、Local Moran 的参考计算接入 `evaluators/`。
4. 用 Playwright 检查真实地图图层状态。
