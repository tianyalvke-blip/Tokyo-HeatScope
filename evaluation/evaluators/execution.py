from __future__ import annotations

from typing import Any
from .base import BaseEvaluator


class ExecutionSuccessEvaluator(BaseEvaluator):
    name = "execution_success"

    def evaluate(self, case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        final = str(result.get("final_answer") or "").strip()
        unrecovered = [event for event in result.get("trace", []) if event.get("type") == "error"]
        passed = bool(final) and not result.get("error") and not unrecovered
        return {"name": self.name, "passed": passed,
                "details": {"has_final_answer": bool(final), "error": result.get("error"), "unrecovered_errors": len(unrecovered)}}


class TraceCompletenessEvaluator(BaseEvaluator):
    name = "trace_completeness"

    def evaluate(self, case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        types = [event.get("type") for event in result.get("trace", [])]
        required = ["user_input", "final_answer"]
        missing = [event_type for event_type in required if event_type not in types]
        return {"name": self.name, "passed": not missing, "details": {"event_types": types, "missing": missing}}
