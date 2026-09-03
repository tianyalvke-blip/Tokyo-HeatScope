"""Lightweight local web dashboard for the GLEN Agent eval harness."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from run_eval import read_jsonl
from evaluators.rules import evaluate_case

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"
TRACES = ROOT / "traces"
REPORTS = ROOT / "reports"
UI = ROOT / "ui"
REAL_STATUS = {"state": "idle", "run_id": None, "suite": None, "total": 0, "completed": 0}


def evaluate(cases_path: Path, traces_path: Path) -> dict:
    cases = read_jsonl(cases_path)
    traces = {row.get("case_id", row.get("id")): row for row in read_jsonl(traces_path)}
    results = [evaluate_case(case, traces.get(case["id"])) for case in cases]
    by_category = {}
    for category in sorted({row.get("category", "unknown") for row in results}):
        subset = [row for row in results if row.get("category") == category]
        by_category[category] = {
            "passed": sum(row["passed"] for row in subset),
            "total": len(subset),
        }
    passed = sum(row["passed"] for row in results)
    return {
        "schema_version": "0.1.0",
        "cases_file": str(cases_path),
        "traces_file": str(traces_path),
        "summary": {"passed": passed, "total": len(results), "pass_rate": passed / len(results) if results else 0},
        "by_category": by_category,
        "results": results,
    }


def load_suite(name: str) -> list[dict]:
    allowed = {
        "golden": CASES / "golden.jsonl",
        "core": CASES / "lstagent_core_en.jsonl",
        "multiturn": CASES / "lstagent_multiturn_en.jsonl",
    }
    path = allowed.get(name)
    if not path or not path.exists():
        raise FileNotFoundError(name)
    return read_jsonl(path)


def safe_trace(name: str) -> Path:
    candidate = (TRACES / name).resolve()
    if candidate.parent != TRACES.resolve() or candidate.suffix != ".jsonl":
        raise ValueError("invalid trace file")
    if not candidate.exists():
        raise FileNotFoundError(name)
    return candidate


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI), **kwargs)

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/real-status":
            self._json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            REAL_STATUS.update({key: payload[key] for key in (
                "state", "run_id", "suite", "total", "completed", "current", "message"
            ) if key in payload})
            self._json({"ok": True})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/cases":
            try:
                suite = parse_qs(parsed.query).get("suite", ["core"])[0]
                rows = load_suite(suite)
                self._json({"suite": suite, "cases": [
                    {"id": row["id"], "label": row.get("prompt") or " / ".join(row.get("turns", []))}
                    for row in rows
                ]})
            except FileNotFoundError as exc:
                self._json({"error": str(exc)}, 404)
            return
        if parsed.path == "/api/traces":
            files = sorted(p.name for p in TRACES.glob("*.jsonl"))
            self._json({"traces": files})
            return
        if parsed.path == "/api/evaluate":
            try:
                name = parse_qs(parsed.query).get("trace", ["sample.jsonl"])[0]
                report = evaluate(CASES / "golden.jsonl", safe_trace(name))
                self._json(report)
            except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, 400)
            return
        if parsed.path == "/api/health":
            self._json({"ok": True})
            return
        if parsed.path == "/api/real-status":
            self._json(REAL_STATUS)
            return
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()


def main():
    parser = argparse.ArgumentParser(description="Run the local GLEN eval dashboard")
    parser.add_argument("--port", type=int, default=8170)
    args = parser.parse_args()
    REPORTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"GLEN eval dashboard: http://127.0.0.1:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped")


if __name__ == "__main__":
    main()
