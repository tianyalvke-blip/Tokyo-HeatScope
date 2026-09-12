# HeatScope Agent Evaluation

This layer reuses the current JavaScript Agent through `agents/heatscope_adapter.mjs`.
It does not replace the map application or the Agent loop.

## Run

```powershell
.venv\Scripts\python evaluation\benchmark.py --agent v1.1 --dataset core_v1
.venv\Scripts\python evaluation\benchmark.py --agents v1.0 v1.1 --dataset core_v1 --workers 4
.venv\Scripts\python evaluation\dashboard.py
```

Aliases `baseline` and `latest` resolve through `agents/registry.yaml`; the UI
shows real version numbers (`v1.0`, `v1.1`). Live model execution needs
`HEATSCOPE_LLM_ENDPOINT` and `HEATSCOPE_LLM_API_KEY`. Without both variables,
the adapter uses a deterministic fixture mode to test the real Agent loop,
tool bridge, trace, scoring and storage plumbing without sending API requests.
Fixture scores validate evaluation plumbing only; use live credentials for a
meaningful model-quality comparison.

## Add an Agent release

1. Add `configs/agents/v1.2.yaml`.
2. Register it in `agents/registry.yaml`; move `latest` only after review.
3. Run focused Agent tests and a benchmark.
4. Update `AGENT_VERSIONING.md`, then create the matching Git tag.

## Data and traces

- Dataset: `evaluation/datasets/<name>.jsonl`
- DuckDB: `evaluation/results/runs.duckdb`
- Raw result/trace: `evaluation/results/raw/<run_id>/`
- Evaluators: `evaluation/evaluators/`

Normalized trace contains observable `user_input`, routing, LLM call metadata,
tool call/result, SQL/RAG/map events, retry/error and final answer. Raw payloads
remain in the per-case JSON file. Hidden model reasoning is never stored.
