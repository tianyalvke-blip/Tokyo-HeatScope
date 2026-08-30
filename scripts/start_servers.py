"""start_servers.py — launch the GLEN LST Agent servers as detached processes.

Spawns:
  * MCP data server   (FastMCP / DuckDB)   -> http://127.0.0.1:8765/mcp
  * Static web server (Range + CORS)       -> http://localhost:8100

Processes are started DETACHED so they survive this script's exit. PIDs are
written to server/.pids. Stop them with stop_servers.py.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv" / "Scripts" / "python.exe"
PIDS = ROOT / "server" / ".pids"

DETACHED = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0)

MCP_PORT = int(os.environ.get("GLEN_MCP_PORT", "8765"))
WEB_PORT = int(os.environ.get("GLEN_SERVE_PORT", "8100"))


def spawn(name, script, cwd, port):
    out = ROOT / "server" / f"{name}.log"
    err = ROOT / "server" / f"{name}.err.log"
    with open(out, "a", encoding="utf-8") as fo, open(err, "a", encoding="utf-8") as fe:
        proc = subprocess.Popen(
            [str(PY), str(script)],
            cwd=str(cwd),
            stdout=fo,
            stderr=fe,
            creationflags=DETACHED,
            close_fds=True,
        )
    print(f"[start] {name} (pid {proc.pid}) -> port {port}")
    return proc.pid


def main():
    pids = {}
    pids["mcp"] = spawn("mcp", ROOT / "server" / "mcp_data_server.py", ROOT, MCP_PORT)
    pids["web"] = spawn("web", ROOT / "server" / "serve.py", ROOT, WEB_PORT)
    PIDS.write_text("\n".join(f"{k} {v}" for k, v in pids.items()), encoding="utf-8")
    print(f"[start] pids written to {PIDS}")


if __name__ == "__main__":
    main()
