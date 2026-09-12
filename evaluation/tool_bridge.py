"""One-shot bridge from the Node adapter to existing MCP tool implementations.

It invokes the already-used server functions directly; it does not duplicate
DuckDB, Local Moran, RF or policy-RAG logic for benchmarks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    request = json.load(sys.stdin)
    try:
        from server import mcp_data_server
        name, args = request["name"], request.get("args", {})
        tool = getattr(mcp_data_server, name, None)
        if not callable(tool):
            raise ValueError(f"TOOL_NOT_FOUND: {name}")
        result = tool(**args)
        print(json.dumps({"success": True, "result": result}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": f"TOOL_EXECUTION_ERROR: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
