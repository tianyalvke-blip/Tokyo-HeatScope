from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import duckdb


class ResultStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(path))
        self.con.execute("""
        create table if not exists benchmark_runs(run_id varchar primary key, dataset_version varchar, started_at varchar,
          finished_at varchar, git_commit varchar, manifest_json varchar);
        create table if not exists case_results(run_id varchar, case_id varchar, agent_version varchar, final_answer varchar,
          status varchar, latency_ms bigint, input_tokens bigint, output_tokens bigint, error varchar, raw_path varchar);
        create table if not exists trace_events(run_id varchar, case_id varchar, agent_version varchar, step integer,
          timestamp varchar, type varchar, name varchar, input_json varchar, output_json varchar, success boolean,
          duration_ms double, metadata_json varchar);
        create table if not exists scores(run_id varchar, case_id varchar, agent_version varchar, evaluator varchar,
          passed boolean, details_json varchar);
        create table if not exists agent_versions(run_id varchar, agent_version varchar, manifest_json varchar);
        """)

    def save_run(self, run: dict[str, Any]) -> None:
        self.con.execute("insert into benchmark_runs values (?, ?, ?, ?, ?, ?)", [run["run_id"], run["dataset_version"], run["started_at"], run.get("finished_at"), run["git_commit"], json.dumps(run["manifest"])])

    def finish_run(self, run_id: str, finished_at: str) -> None:
        self.con.execute("update benchmark_runs set finished_at=? where run_id=?", [finished_at, run_id])

    def save_result(self, run_id: str, result: dict[str, Any], scores: list[dict[str, Any]], raw_path: str) -> None:
        status = "error" if result.get("error") else "success"
        self.con.execute("insert into case_results values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [run_id, result["case_id"], result["agent_version"], result.get("final_answer", ""), status, result.get("latency_ms"), result.get("input_tokens"), result.get("output_tokens"), result.get("error"), raw_path])
        for event in result.get("trace", []):
            self.con.execute("insert into trace_events values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [run_id, result["case_id"], result["agent_version"], event.get("step"), event.get("timestamp"), event.get("type"), event.get("name"), json.dumps(event.get("input"), ensure_ascii=False), json.dumps(event.get("output"), ensure_ascii=False), event.get("success"), event.get("duration_ms"), json.dumps(event.get("metadata", {}), ensure_ascii=False)])
        for score in scores:
            self.con.execute("insert into scores values (?, ?, ?, ?, ?, ?)", [run_id, result["case_id"], result["agent_version"], score["name"], score["passed"], json.dumps(score.get("details", {}), ensure_ascii=False)])
        self.con.execute("insert into agent_versions values (?, ?, ?)", [run_id, result["agent_version"], json.dumps(result.get("manifest", {}), ensure_ascii=False)])

    def close(self) -> None:
        self.con.close()
