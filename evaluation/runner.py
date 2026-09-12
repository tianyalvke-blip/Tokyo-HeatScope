from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

from evaluation.agent_loader import AgentRegistry, git_commit, load_agent
from evaluation.evaluators import DEFAULT_EVALUATORS
from evaluation.storage import ResultStore

ROOT = Path(__file__).resolve().parents[1]


def load_dataset(name: str) -> list[dict[str, Any]]:
    path = ROOT / "evaluation" / "datasets" / f"{name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(case: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    return [evaluator.evaluate(case, result) for evaluator in DEFAULT_EVALUATORS]


def resolve_stacks(names: list[str]) -> list[dict[str, Any]]:
    registry = yaml.safe_load((ROOT / "stacks" / "registry.yaml").read_text(encoding="utf-8"))
    app_registry = yaml.safe_load((ROOT / "apps" / "registry.yaml").read_text(encoding="utf-8"))
    targets = []
    for requested in names:
        stack_id = registry.get("aliases", {}).get(requested, requested)
        stack = registry.get("versions", {}).get(stack_id)
        if not stack:
            raise ValueError(f"Unknown Stack '{requested}'")
        app_id = app_registry.get("aliases", {}).get(stack["app"], stack["app"])
        app_entry = app_registry["versions"].get(app_id)
        app_manifest = yaml.safe_load((ROOT / app_entry["config"]).read_text(encoding="utf-8"))
        data_manifest = yaml.safe_load((ROOT / "configs" / "data" / f"{stack['data']}.yaml").read_text(encoding="utf-8"))
        targets.append({"label": stack_id, "agent": stack["agent"], "stack": {"stack_id": stack_id, "app": app_manifest, "data": data_manifest, "purpose": stack.get("purpose")}})
    return targets


async def run_benchmark(versions: list[str], dataset_name: str, *, workers: int = 1,
                        timeout_s: int = 180, overrides: dict[str, Any] | None = None,
                        stack_names: list[str] | None = None) -> tuple[str, list[dict[str, Any]]]:
    cases = load_dataset(dataset_name)
    registry = AgentRegistry()
    targets = resolve_stacks(stack_names) if stack_names else [{"label": registry.resolve(version)[0], "agent": registry.resolve(version)[0], "stack": None} for version in versions]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"{stamp}_{dataset_name}"
    results_dir = ROOT / "evaluation" / "results"
    raw_dir = results_dir / "raw" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    store = ResultStore(results_dir / "runs.duckdb")
    manifest = {target["label"]: {**load_agent(target["agent"], timeout_s=timeout_s).manifest(overrides or {}), "stack": target["stack"]} for target in targets}
    run = {"run_id": run_id, "dataset_version": dataset_name, "started_at": datetime.now(timezone.utc).isoformat(),
           "git_commit": git_commit(), "manifest": manifest}
    store.save_run(run)
    sem = asyncio.Semaphore(max(1, workers))

    async def one(case: dict[str, Any], target: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        async with sem:
            adapter = load_agent(target["agent"], timeout_s=timeout_s)
            result = await adapter.run(case["query"], case["case_id"], overrides)
            result["agent_version"] = target["label"]
            result.setdefault("manifest", {})["stack"] = target["stack"]
            scores = evaluate(case, result)
            raw_path = raw_dir / f"{case['case_id']}__{target['label']}.json"
            raw_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            store.save_result(run_id, result, scores, str(raw_path.relative_to(ROOT)))
            return result, scores

    try:
        gathered = await asyncio.gather(*(one(case, target) for target in targets for case in cases), return_exceptions=True)
        output = []
        for item in gathered:
            if isinstance(item, Exception):
                output.append({"error": str(item)})
            else:
                result, scores = item
                output.append({"result": result, "scores": scores})
        return run_id, output
    finally:
        store.finish_run(run_id, datetime.now(timezone.utc).isoformat())
        store.close()
