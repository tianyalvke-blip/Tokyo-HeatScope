"""Run the first dependency-free GLEN Agent golden-trace evaluation."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluators.rules import evaluate_case


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL at {path}:{line_no}: {exc}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("evals/cases/golden.jsonl"))
    parser.add_argument("--traces", type=Path, default=Path("evals/traces/latest.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("evals/reports/latest.json"))
    args = parser.parse_args()

    cases = read_jsonl(args.cases)
    trace_rows = {row.get("case_id", row.get("id")): row for row in read_jsonl(args.traces)}
    results = [evaluate_case(case, trace_rows.get(case["id"])) for case in cases]
    passed = sum(1 for row in results if row["passed"])
    by_category = {}
    for category in sorted({row["category"] for row in results}):
        subset = [row for row in results if row["category"] == category]
        by_category[category] = {
            "passed": sum(1 for row in subset if row["passed"]),
            "total": len(subset),
        }
    report = {
        "schema_version": "0.1.0",
        "cases_file": str(args.cases),
        "traces_file": str(args.traces),
        "summary": {"passed": passed, "total": len(results), "pass_rate": passed / len(results) if results else 0},
        "by_category": by_category,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GLEN eval: {passed}/{len(results)} passed ({report['summary']['pass_rate']:.1%})")
    for category, stats in by_category.items():
        print(f"  {category}: {stats['passed']}/{stats['total']}")
    print(f"Report: {args.output}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
