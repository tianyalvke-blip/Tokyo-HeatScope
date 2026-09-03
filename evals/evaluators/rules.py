"""Dependency-free evaluators for GLEN Agent golden traces."""

from __future__ import annotations

import re
from typing import Any


def _tool_name(call: dict[str, Any]) -> str:
    return str(call.get("name") or call.get("function", {}).get("name") or "")


def _tool_args(call: dict[str, Any]) -> dict[str, Any]:
    args = call.get("args", call.get("arguments", call.get("function", {}).get("arguments", {})))
    if isinstance(args, str):
        import json
        try:
            args = json.loads(args)
        except Exception:
            return {}
    return args if isinstance(args, dict) else {}


def _contains_subset(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and _contains_subset(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and all(item in actual for item in expected)
    return actual == expected


def evaluate_case(case: dict[str, Any], trace: dict[str, Any] | None) -> dict[str, Any]:
    failures: list[str] = []
    if trace is None:
        return {"id": case["id"], "category": case.get("category"), "passed": False, "failures": ["missing trace"]}

    if trace.get("error"):
        failures.append(f"runtime error: {trace['error']}")

    calls = trace.get("tool_calls", [])
    actual_names = [_tool_name(c) if isinstance(c, dict) else str(c) for c in calls]
    expected = case.get("expected_tools", [])
    expected_names = [e.get("name", "") if isinstance(e, dict) else str(e) for e in expected]
    if actual_names != expected_names:
        failures.append(f"tool trajectory mismatch: expected {expected_names}, got {actual_names}")

    for idx, spec in enumerate(expected):
        if not isinstance(spec, dict) or "args" not in spec or idx >= len(calls):
            continue
        actual_args = _tool_args(calls[idx])
        if not _contains_subset(actual_args, spec["args"]):
            failures.append(f"tool args mismatch at {idx}: expected subset {spec['args']}, got {actual_args}")

    answer = str(trace.get("final_answer") or "")
    answer_lower = answer.lower()
    for phrase in case.get("must_include", []):
        if phrase.lower() not in answer_lower:
            failures.append(f"missing required phrase: {phrase}")
    for phrase in case.get("must_not_include", []):
        if phrase.lower() in answer_lower:
            failures.append(f"forbidden phrase present: {phrase}")

    # Optional regular-expression assertions can be added per case later.
    for pattern in case.get("must_match", []):
        if not re.search(pattern, answer, flags=re.IGNORECASE | re.DOTALL):
            failures.append(f"missing required pattern: {pattern}")

    return {
        "id": case["id"],
        "category": case.get("category", "unknown"),
        "passed": not failures,
        "failures": failures,
        "actual_tools": actual_names,
        "latency_ms": trace.get("latency_ms"),
    }
