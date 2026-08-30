"""
python_runner.py — isolated, timeout-guarded execution of user Python snippets.

Used by `run_python()` for ad-hoc analysis (e.g. quick linear regressions on
the Tokyo LST grid). Failures are fully contained: a syntax error, runtime
error, timeout, or memory blow-up fails only this one call — never the FastMCP
server, the DuckDB connection, the agent, or the static server.

Security note: this executes arbitrary Python with the same user privileges as
the server process. It is a "notebook-style kernel" for a local research tool,
not a hardened sandbox — do not expose it to untrusted users.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET = PROJECT_ROOT / "app" / "data" / "tokyo_lst_grid.parquet"
PYTHON = sys.executable

_WRAPPER = r'''
import sys, json, traceback
import numpy as np
import pandas as pd
import scipy
import sklearn

NS = dict(
    np=np, pd=pd, scipy=scipy, sklearn=sklearn,
    df=pd.read_parquet(PARQUET_ABS),
)

def _default(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.Series):
        return o.tolist()
    if isinstance(o, pd.DataFrame):
        return o.to_dict("records")
    raise TypeError("not JSON-serializable: " + repr(type(o)))

def _emit(payload):
    print("__GLEN_RESULT__ " + json.dumps(payload, default=_default, ensure_ascii=False))

try:
    exec(compile(CODE, "<user_code>", "exec"), NS)
except BaseException:
    _emit({"success": False, "error": traceback.format_exc()})
else:
    _emit({"success": True, "result": NS.get("__result__")})
'''


def run_python(code: str, timeout: int = 30):
    """Run `code` in an isolated subprocess.

    `df` (pandas DataFrame of the Tokyo LST grid) plus numpy / pandas / scipy /
    sklearn are pre-loaded. Set `__result__` to return a value (JSON-safe);
    prints are captured too.

    Returns {"success": bool, "result"|"error": ...}.
    """
    if not code or not code.strip():
        return {"success": False, "error": "empty code"}
    script = (
        _WRAPPER
        .replace("PARQUET_ABS", json.dumps(str(PARQUET)))
        .replace("CODE", json.dumps(code))
    )
    try:
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run(
                [PYTHON, "-c", script],
                capture_output=True,
                text=True,
                cwd=td,
                timeout=max(1, int(timeout)),
            )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"execution timed out after {timeout}s"}
    except Exception as exc:  # pragma: no cover
        return {"success": False, "error": f"runner failed to start: {exc}"}

    out = (proc.stdout or "") + (proc.stderr or "")
    marker = "__GLEN_RESULT__ "
    idx = out.rfind(marker)
    if idx == -1:
        return {
            "success": False,
            "error": f"runner produced no result (exit {proc.returncode})\n{out[:2000]}",
        }
    line = out[idx + len(marker):].strip()
    try:
        return json.loads(line)
    except Exception:
        return {"success": False, "error": f"bad result payload:\n{line[:1000]}"}
