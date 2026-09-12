# HeatScope Evaluator version management

The Evaluator version owns scoring logic only. It does not define the tested
App, Agent, UI, dataset or benchmark trace schema.

| Evaluator release | Git tag | Scope |
|---|---|---|
| v1.0.0 | `evaluator-v1.0.0` | Deterministic tool selection, tool-argument, execution-success and trace-completeness checks. |

Every benchmark run records its evaluator manifest in `benchmark_runs.manifest_json`.
That means historical raw traces can be rescored later by a new evaluator
without rerunning the Agent.

Use a patch release for scoring bug fixes, a minor release when metrics or
thresholds change, and a major release when score meanings are incompatible.
New evaluator implementations belong in `evaluation/evaluators/`; register the
chosen evaluator set in `configs/evaluators/` and `evaluators/registry.yaml`.
