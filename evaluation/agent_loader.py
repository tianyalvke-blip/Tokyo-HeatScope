"""Registry lookup and the Python-to-Node adapter boundary."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


class AgentRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or ROOT / "agents" / "registry.yaml"
        self.data = yaml.safe_load(self.path.read_text(encoding="utf-8"))

    def resolve(self, requested: str) -> tuple[str, dict[str, Any]]:
        version = self.data.get("aliases", {}).get(requested, requested)
        entry = self.data.get("versions", {}).get(version)
        if not entry:
            known = sorted([*self.data.get("versions", {}), *self.data.get("aliases", {})])
            raise ValueError(f"Unknown Agent version '{requested}'. Known: {', '.join(known)}")
        config_path = ROOT / entry["config"]
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        return version, config


class HeatScopeAgentAdapter:
    """Runs the existing JavaScript Agent in a fresh Node process per case."""

    def __init__(self, version: str, config: dict[str, Any], *, timeout_s: int = 180) -> None:
        self.version = version
        self.config = config
        self.timeout_s = timeout_s

    async def run(self, query: str, case_id: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {"query": query, "case_id": case_id, "agent_version": self.version,
                   "manifest": self.manifest(overrides or {}), "overrides": overrides or {}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(request, handle, ensure_ascii=False)
            request_path = Path(handle.name)
        try:
            process = await asyncio.create_subprocess_exec(
                "node", str(ROOT / "agents" / "heatscope_adapter.mjs"), str(request_path),
                cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "HEATSCOPE_BENCHMARK": "1"},
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout_s)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return self._error_result(query, case_id, "TIMEOUT")
            if process.returncode != 0:
                return self._error_result(query, case_id, stderr.decode("utf-8", "replace")[-1000:] or "NODE_ADAPTER_ERROR")
            return json.loads(stdout.decode("utf-8"))
        finally:
            request_path.unlink(missing_ok=True)

    def manifest(self, overrides: dict[str, Any]) -> dict[str, Any]:
        model = {**self.config.get("model", {}), **overrides.get("model", {})}
        return {
            "agent_version": self.version,
            "agent_id": self.config.get("agent_id"),
            "release_tag": self.config.get("release_tag"),
            "implementation_commit": self.config.get("implementation_commit"),
            "git_commit": git_commit(),
            "model": model.get("name"),
            "temperature": model.get("temperature", 0),
            "planner_version": self.config.get("planner", {}).get("type"),
            "toolset_version": self.config.get("tools", {}).get("profile"),
            "rag_version": self.config.get("rag", {}).get("version"),
            "rf_version": self.config.get("rf", {}).get("version"),
            "max_steps": overrides.get("max_steps", self.config.get("planner", {}).get("max_steps")),
            "intent_gateway": self.config.get("intent_gateway", {}).get("enabled", False),
        }

    def _error_result(self, query: str, case_id: str, error: str) -> dict[str, Any]:
        return {"case_id": case_id, "agent_version": self.version, "final_answer": "", "trace": [
            {"step": 1, "timestamp": None, "type": "user_input", "name": "user_query", "input": {"query": query}, "output": None, "success": True, "duration_ms": 0, "metadata": {}},
            {"step": 2, "timestamp": None, "type": "error", "name": "adapter", "input": None, "output": {"error": error}, "success": False, "duration_ms": 0, "metadata": {"code": error}},
        ], "tool_calls": [], "tool_results": [], "map_actions": [], "retrievals": [], "latency_ms": 0,
                "input_tokens": None, "output_tokens": None, "error": error, "manifest": self.manifest({})}


def load_agent(version: str, *, timeout_s: int = 180) -> HeatScopeAgentAdapter:
    resolved, config = AgentRegistry().resolve(version)
    return HeatScopeAgentAdapter(resolved, config, timeout_s=timeout_s)
