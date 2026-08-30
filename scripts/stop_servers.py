"""stop_servers.py — stop the GLEN LST Agent servers started by start_servers.py."""

import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIDS = ROOT / "server" / ".pids"


def main():
    if not PIDS.exists():
        print("[stop] no .pids file — nothing to do")
        return
    for line in PIDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, pid_s = line.partition(" ")
        if not pid_s.isdigit():
            continue
        pid = int(pid_s)
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"[stop] {name} pid {pid} -> SIGTERM")
        except OSError as e:
            print(f"[stop] {name} pid {pid}: {e}")
    PIDS.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
