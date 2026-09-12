"""Local-only Cal-style browser for saved benchmark runs.

Run: .venv\\Scripts\\python evaluation\\dashboard.py
Then open http://127.0.0.1:8844.
"""
from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "evaluation" / "results" / "runs.duckdb"

HTML = r'''<!doctype html><meta charset="utf-8"><title>HeatScope · Agent Evaluation</title>
<style>
:root{--ink:#182934;--muted:#667784;--line:#dbe4e7;--paper:#f7f9f8;--card:#fff;--blue:#1775bd;--blue-soft:#eaf4fb;--green:#27755a;--red:#b74a43}*{box-sizing:border-box}body{margin:0;background:var(--paper);font:14px/1.55 Inter,system-ui,"Noto Sans SC",sans-serif;color:var(--ink)}header{padding:28px max(28px,calc((100vw - 1120px)/2));background:#102a38;color:#fff}header p{margin:5px 0 0;color:#bdd2db}main{max-width:1120px;margin:auto;padding:28px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px}.controls{display:flex;gap:12px;align-items:end;flex-wrap:wrap}.field{display:grid;gap:5px;color:var(--muted);font-size:12px}.field select{min-width:145px;border:1px solid var(--line);border-radius:8px;padding:9px;background:#fff;color:var(--ink)}button{border:0;border-radius:8px;background:var(--blue);color:#fff;padding:10px 15px;font-weight:700;cursor:pointer}button:hover{filter:brightness(.95)}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-size:12px}.tag{border-radius:99px;padding:3px 8px;background:var(--blue-soft);color:var(--blue);font-weight:700;font-size:12px}.ok{color:var(--green);font-weight:700}.bad{color:var(--red);font-weight:700}.trace{white-space:pre-wrap;background:#102a38;color:#eaf4fb;border-radius:10px;padding:14px;max-height:420px;overflow:auto;font:12px/1.5 ui-monospace,Consolas,monospace}.hint{color:var(--muted)}@media(max-width:640px){main{padding:14px}header{padding:22px}.card{padding:14px}}
</style><header><strong>HeatScope</strong> <span class="tag">Agent Evaluation</span><p>Compare observable execution, not hidden reasoning.</p></header><main>
<section class="card"><div class="controls"><label class="field">Agent A<select id="a"><option>v1.0</option><option selected>v1.1</option></select></label><label class="field">Agent B<select id="b"><option selected>v1.1</option><option>v1.0</option></select></label><label class="field">Dataset<select id="dataset"><option>core_v1</option></select></label><label class="field">Workers<select id="workers"><option>1</option><option>2</option><option>4</option></select></label><button onclick="run()">Run benchmark</button></div><p id="status" class="hint">Runs locally and saves results to DuckDB.</p></section>
<section class="card"><h2>Saved runs</h2><div id="runs" class="hint">Loading…</div></section><section class="card"><h2>Case results</h2><div id="results" class="hint">Select a run.</div></section><section class="card"><h2>Trace comparison</h2><div id="trace" class="hint">Select a case result to inspect normalized events.</div></section></main>
<script>
async function api(path,opt){let r=await fetch(path,opt);return r.json()} async function load(){let runs=await api('/api/runs');document.querySelector('#runs').innerHTML=runs.length?'<table><tr><th>Run</th><th>Dataset</th><th>Started</th><th>Action</th></tr>'+runs.map(x=>`<tr><td><span class=tag>${x.run_id}</span></td><td>${x.dataset_version}</td><td>${x.started_at}</td><td><button onclick="showRun('${x.run_id}')">View</button></td></tr>`).join('')+'</table>':'No runs yet.'} async function showRun(id){let d=await api('/api/run/'+encodeURIComponent(id));document.querySelector('#results').innerHTML='<table><tr><th>Case</th><th>Agent</th><th>Status</th><th>Latency</th><th>Trace</th></tr>'+d.results.map(x=>`<tr><td>${x.case_id}</td><td><span class=tag>${x.agent_version}</span></td><td class=${x.status==='success'?'ok':'bad'}>${x.status}</td><td>${(x.latency_ms/1000).toFixed(2)}s</td><td><button onclick="showTrace('${id}','${x.case_id}','${x.agent_version}')">Inspect</button></td></tr>`).join('')+'</table>'} async function showTrace(run,caseId,version){let d=await api(`/api/trace/${encodeURIComponent(run)}/${caseId}/${version}`);document.querySelector('#trace').innerHTML='<div class=trace>'+d.map(e=>`${e.step}. ${e.type} · ${e.name||'-'}\n${JSON.stringify(e.input||e.output||{},null,2)}`).join('\n\n')+'</div>'} async function run(){let a=document.querySelector('#a').value,b=document.querySelector('#b').value,ds=document.querySelector('#dataset').value,w=document.querySelector('#workers').value;document.querySelector('#status').textContent='Benchmark started…';let r=await api('/api/benchmark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agents:[a,b],dataset:ds,workers:w})});document.querySelector('#status').textContent=r.message;setTimeout(load,2500)} load();
</script>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            data = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
        if not DB.exists(): return self.send_json([])
        con = duckdb.connect(str(DB), read_only=True)
        try:
            if path == "/api/runs":
                rows = con.execute("select run_id,dataset_version,started_at from benchmark_runs order by started_at desc limit 30").fetchall(); return self.send_json([dict(zip(["run_id","dataset_version","started_at"], row)) for row in rows])
            parts = path.split("/")
            if len(parts) == 4 and parts[2] == "run":
                rows = con.execute("select case_id,agent_version,status,latency_ms from case_results where run_id=? order by case_id,agent_version", [parts[3]]).fetchall(); return self.send_json({"results":[dict(zip(["case_id","agent_version","status","latency_ms"], row)) for row in rows]})
            if len(parts) == 6 and parts[2] == "trace":
                rows = con.execute("select step,timestamp,type,name,input_json,output_json,success,duration_ms,metadata_json from trace_events where run_id=? and case_id=? and agent_version=? order by step", parts[3:]).fetchall(); return self.send_json([{"step":r[0],"timestamp":r[1],"type":r[2],"name":r[3],"input":json.loads(r[4] or "null"),"output":json.loads(r[5] or "null"),"success":r[6],"duration_ms":r[7],"metadata":json.loads(r[8] or "{}") } for r in rows])
            self.send_error(404)
        finally: con.close()
    def do_POST(self):
        if self.path != "/api/benchmark": return self.send_error(404)
        try:
            body=json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            agents=body.get("agents", ["v1.0","v1.1"]); dataset=body.get("dataset", "core_v1"); workers=str(body.get("workers",1))
            subprocess.Popen([sys.executable, "evaluation/benchmark.py", "--agents", *agents, "--dataset", dataset, "--workers", workers], cwd=ROOT)
            self.send_json({"message":"Benchmark started. Refreshing saved runs shortly."})
        except Exception as exc: self.send_json({"message":f"Could not start benchmark: {exc}"})


if __name__ == "__main__":
    print("HeatScope Evaluation Dashboard: http://127.0.0.1:8844")
    ThreadingHTTPServer(("127.0.0.1", 8844), Handler).serve_forever()
