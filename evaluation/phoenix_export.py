"""Export observable HeatScope benchmark traces to a local Phoenix workspace.

Run this script with ``evaluation/.phoenix-venv/Scripts/python.exe`` while
Phoenix is serving on http://127.0.0.1:6006. It never exports hidden reasoning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from phoenix.otel import register
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "evaluation" / "results" / "raw"


def latest_run() -> Path:
    runs = [path for path in RAW_ROOT.iterdir() if path.is_dir()]
    if not runs:
        raise FileNotFoundError("No benchmark raw traces found. Run a benchmark first.")
    return max(runs, key=lambda path: path.stat().st_mtime)


def event_output(events: list[dict], index: int) -> object:
    """Find the paired tool result without retaining unrelated raw payloads."""
    call = events[index]
    for event in events[index + 1 :]:
        if event.get("type") == "tool_result" and event.get("name") == call.get("name"):
            return event.get("output")
    return None


def export(run_dir: Path) -> int:
    provider = register(
        endpoint="http://127.0.0.1:6006/v1/traces",
        project_name="HeatScope Evaluation",
        protocol="http/protobuf",
        batch=False,
        verbose=False,
    )
    tracer = provider.get_tracer("heatscope.benchmark")
    count = 0
    for path in sorted(run_dir.glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        events = result.get("trace", [])
        attributes = {
            SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.CHAIN.value,
            SpanAttributes.INPUT_VALUE: result.get("query") or next(
                (event.get("input", {}).get("query") for event in events if event.get("type") == "user_input"), ""
            ),
            SpanAttributes.OUTPUT_VALUE: result.get("final_answer", ""),
            SpanAttributes.SESSION_ID: result.get("run_id", run_dir.name),
            "heatscope.run_id": run_dir.name,
            "heatscope.case_id": result.get("case_id", path.stem.split("__")[0]),
            "heatscope.stack_id": result.get("agent_version", "unknown"),
            "heatscope.status": result.get("status", "success"),
        }
        with tracer.start_as_current_span("HeatScope benchmark case", attributes=attributes):
            for index, event in enumerate(events):
                if event.get("type") != "tool_call":
                    continue
                with tracer.start_as_current_span(
                    event.get("name") or "tool",
                    attributes={
                        SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.TOOL.value,
                        SpanAttributes.INPUT_VALUE: json.dumps(event.get("input") or {}, ensure_ascii=False),
                        SpanAttributes.OUTPUT_VALUE: json.dumps(event_output(events, index), ensure_ascii=False),
                        "heatscope.success": bool(event.get("success", True)),
                        "heatscope.duration_ms": event.get("duration_ms", 0),
                    },
                ):
                    pass
        count += 1
    provider.force_flush()
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export HeatScope benchmark traces to local Phoenix")
    parser.add_argument("--run", help="Raw run directory name; defaults to most recently modified run")
    args = parser.parse_args()
    run_dir = RAW_ROOT / args.run if args.run else latest_run()
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Raw run directory not found: {run_dir}")
    print(f"Exported {export(run_dir)} case traces from {run_dir.name} to Phoenix.")
