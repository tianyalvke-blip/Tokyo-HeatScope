from __future__ import annotations

from collections import defaultdict
from typing import Any


def passed(scores: list[dict[str, Any]]) -> bool:
    return bool(scores) and all(score.get("passed") for score in scores)


def summarize(run_items: list[dict[str, Any]], versions: list[str]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in run_items:
        if "result" in item:
            grouped[item["result"]["agent_version"]].append(item)
    lines = ["\nHeatScope Benchmark\n", "Agent       Cases  Success  Tool select  Arguments  Execution  Avg latency"]
    for version in versions:
        items = grouped.get(version, [])
        count = len(items) or 1
        def rate(name: str) -> float:
            return 100 * sum(next((s["passed"] for s in item["scores"] if s["name"] == name), False) for item in items) / count
        latency = sum(item["result"].get("latency_ms", 0) or 0 for item in items) / count / 1000
        success = 100 * sum(passed(item["scores"]) for item in items) / count
        lines.append(f"{version:<11} {len(items):>5}  {success:>6.1f}%  {rate('tool_selection'):>9.1f}%  {rate('tool_arguments'):>8.1f}%  {rate('execution_success'):>9.1f}%  {latency:>8.2f}s")
    if len(versions) >= 2:
        left, right = versions[:2]
        by_key = {(item["result"]["case_id"], item["result"]["agent_version"]): item for item in run_items if "result" in item}
        improved, regressed, both_passed, both_failed = [], [], [], []
        cases = sorted({key[0] for key in by_key})
        for case in cases:
            a, b = by_key.get((case, left)), by_key.get((case, right))
            if not a or not b: continue
            ap, bp = passed(a["scores"]), passed(b["scores"])
            if not ap and bp: improved.append(case)
            elif ap and not bp: regressed.append(case)
            elif ap: both_passed.append(case)
            else: both_failed.append(case)
        lines += ["", f"Improved: {len(improved)}  {', '.join(improved) or '-'}", f"Regressed: {len(regressed)}  {', '.join(regressed) or '-'}", f"Both passed: {len(both_passed)}  Both failed: {len(both_failed)}"]
    return "\n".join(lines)


def trace_diff(left: dict[str, Any], right: dict[str, Any]) -> str:
    def compact(result: dict[str, Any]) -> list[str]:
        return [f"{event.get('step')}. {event.get('type')} · {event.get('name') or '-'} · {event.get('input') or ''}" for event in result.get("trace", []) if event.get("type") in {"router_decision", "planner_decision", "tool_call", "tool_result", "map_action", "error", "final_answer"}]
    return "\n".join([f"{left['agent_version']}", *compact(left), "", f"{right['agent_version']}", *compact(right)])
