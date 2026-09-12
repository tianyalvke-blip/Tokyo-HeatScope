"""CLI: python evaluation/benchmark.py --agents v1.0 v1.1 --dataset core_v1 --workers 4"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.compare import summarize
from evaluation.runner import run_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description="HeatScope Agent benchmark")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agent", help="One registry version or alias")
    group.add_argument("--agents", nargs="+", help="Two or more registry versions or aliases")
    group.add_argument("--stack", help="One complete App + Agent + Data stack")
    group.add_argument("--stacks", nargs="+", help="Two or more complete stacks")
    parser.add_argument("--dataset", required=True, help="Dataset basename, e.g. core_v1")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--model", help="Reserved component override")
    parser.add_argument("--max-steps", type=int, help="Reserved component override")
    args = parser.parse_args()
    versions = args.agents or ([args.agent] if args.agent else [])
    stacks = args.stacks or ([args.stack] if args.stack else None)
    overrides = {k: v for k, v in {"model": {"name": args.model} if args.model else None, "max_steps": args.max_steps}.items() if v is not None}
    run_id, items = asyncio.run(run_benchmark(versions, args.dataset, workers=args.workers, timeout_s=args.timeout, overrides=overrides, stack_names=stacks))
    print(f"Run: {run_id}")
    print(summarize(items, stacks or versions))
    print(f"\nStored: evaluation/results/runs.duckdb\nRaw traces: evaluation/results/raw/{run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
