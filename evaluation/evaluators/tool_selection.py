from __future__ import annotations

from typing import Any
from .base import BaseEvaluator


def _calls(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [event for event in result.get("trace", []) if event.get("type") == "tool_call"]


class ToolSelectionEvaluator(BaseEvaluator):
    name = "tool_selection"

    def evaluate(self, case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        required = case.get("expected", {}).get("required_tools", [])
        called = [event.get("name") for event in _calls(result)]
        missing = [tool for tool in required if tool not in called]
        return {"name": self.name, "passed": not missing, "details": {"required": required, "called": called, "missing": missing}}


class ToolArgumentEvaluator(BaseEvaluator):
    name = "tool_arguments"

    def evaluate(self, case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        constraints = case.get("expected", {}).get("tool_constraints", {})
        calls = _calls(result)
        failures = []
        for tool, expected in constraints.items():
            matching = [event for event in calls if event.get("name") == tool]
            if not matching:
                failures.append({"tool": tool, "reason": "not_called"})
                continue
            if not any(all((event.get("input") or {}).get(k) == v for k, v in expected.items()) for event in matching):
                failures.append({"tool": tool, "reason": "argument_mismatch", "expected": expected,
                                 "actual": [event.get("input") for event in matching]})
        return {"name": self.name, "passed": not failures, "details": {"failures": failures}}
