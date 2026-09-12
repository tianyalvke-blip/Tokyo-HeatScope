"""Local-only Cal-style dashboard for launching and inspecting benchmarks."""
from __future__ import annotations

import json, subprocess, sys, threading, time, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "evaluation" / "results" / "runs.duckdb"
JOBS: dict[str, dict] = {}

HTML = r'''<!doctype html><meta charset="utf-8"><title>HeatScope · Agent Evaluation</title>
<style>:root{--ink:#182934;--muted:#667784;--line:#dbe4e7;--paper:#f7f9f8;--card:#fff;--blue:#1775bd;--blue-soft:#eaf4fb;--green:#27755a;--red:#b74a43}*{box-sizing:border-box}body{margin:0;background:var(--paper);font:14px/1.55 Inter,system-ui,"Noto Sans SC",sans-serif;color:var(--ink)}header{padding:28px max(28px,calc((100vw - 1120px)/2));background:#102a38;color:#fff}header p{margin:5px 0 0;color:#bdd2db}main{max-width:1120px;margin:auto;padding:28px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px}.controls,.mode{display:flex;gap:12px;align-items:end;flex-wrap:wrap}.mode{margin-bottom:16px}.field{display:grid;gap:5px;color:var(--muted);font-size:12px}.field select{min-width:150px;border:1px solid var(--line);border-radius:8px;padding:9px;background:#fff;color:var(--ink)}button{border:0;border-radius:8px;background:var(--blue);color:#fff;padding:10px 15px;font-weight:700;cursor:pointer}.mode button{background:#eef3f5;color:var(--ink)}.mode button.active{background:var(--blue);color:#fff}.hidden{display:none!important}.progress{height:8px;background:#e7edef;border-radius:20px;overflow:hidden;margin:12px 0 5px}.progress i{display:block;height:100%;background:var(--blue);width:0%;transition:width .3s}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-size:12px}.tag{border-radius:99px;padding:3px 8px;background:var(--blue-soft);color:var(--blue);font-weight:700;font-size:12px}.ok{color:var(--green);font-weight:700}.bad{color:var(--red);font-weight:700}.trace{white-space:pre-wrap;background:#102a38;color:#eaf4fb;border-radius:10px;padding:14px;max-height:420px;overflow:auto;font:12px/1.5 ui-monospace,Consolas,monospace}.hint{color:var(--muted)}</style>
<header><strong>HeatScope</strong> <span class="tag">Agent Evaluation</span><p>Compare observable execution, not hidden reasoning.</p></header><main>
<section class="card"><div class="mode"><button id="single" class="active" onclick="setMode('single')">Single run</button><button id="compare" onclick="setMode('compare')">Compare versions</button></div><div class="controls"><label class="field">Version A<select id="a"><option>stack-v1.0</option><option selected>stack-v1.1</option></select></label><label class="field" id="bwrap">Version B<select id="b"><option>stack-v1.0</option><option selected>stack-v1.1</option></select></label><label class="field">Dataset<select id="dataset"><option>core_v1</option></select></label><label class="field">Workers<select id="workers"><option>1</option><option>2</option><option>4</option></select></label><button onclick="run()">Run benchmark</button></div><div id="pwrap" class="hidden"><div class="progress"><i id="bar"></i></div><span id="status" class="hint"></span></div></section>
<section class="card"><h2>Saved runs</h2><div id="runs" class="hint">Loading…</div></section><section class="card"><h2>Case resolution</h2><p class="hint">Resolved means every active deterministic evaluator passed for that case.</p><div id="results" class="hint">Select a run.</div></section><section class="card"><h2>Trace and score details</h2><div id="trace" class="hint">Select a case result to inspect normalized events and evaluator outcomes.</div></section></main>
<script>let mode='single',timer=null;const api=(p,o)=>fetch(p,o).then(r=>r.json());function setMode(m){mode=m;single.classList.toggle('active',m==='single');compare.classList.toggle('active',m==='compare');bwrap.classList.toggle('hidden',m==='single')}async function load(){let data=await api('/api/runs');runs.innerHTML=data.length?'<table><tr><th>Run</th><th>Dataset</th><th>Started</th><th>Action</th></tr>'+data.map(x=>`<tr><td><span class=tag>${x.run_id}</span></td><td>${x.dataset_version}</td><td>${x.started_at}</td><td><button onclick="showRun('${x.run_id}')">View</button></td></tr>`).join('')+'</table>':'No runs yet.'}async function showRun(id){let d=await api('/api/run/'+encodeURIComponent(id));results.innerHTML='<table><tr><th>Case</th><th>Version</th><th>Resolution</th><th>Passed checks</th><th>Latency</th><th>Trace</th></tr>'+d.results.map(x=>`<tr><td>${x.case_id}</td><td><span class=tag>${x.agent_version}</span></td><td class=${x.resolved?'ok':'bad'}>${x.resolved?'Resolved':'Needs review'}</td><td>${x.passed_checks}/${x.total_checks}</td><td>${(x.latency_ms/1000).toFixed(2)}s</td><td><button onclick="showTrace('${id}','${x.case_id}','${x.agent_version}')">Inspect</button></td></tr>`).join('')+'</table>'}async function showTrace(run,caseId,version){let d=await api(`/api/trace/${encodeURIComponent(run)}/${caseId}/${version}`);trace.innerHTML='<p><b>Evaluator checks</b></p><ul>'+d.scores.map(x=>`<li class=${x.passed?'ok':'bad'}>${x.evaluator}: ${x.passed?'PASS':'FAIL'}</li>`).join('')+'</ul><div class=trace>'+d.events.map(e=>`${e.step}. ${e.type} · ${e.name||'-'}\n${JSON.stringify(e.input||e.output||{},null,2)}`).join('\n\n')+'</div>'}async function run(){let agents=mode==='single'?[a.value]:[a.value,b.value],r=await api('/api/benchmark',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agents,dataset:dataset.value,workers:workers.value})});pwrap.classList.remove('hidden');status.textContent='Starting…';bar.style.width='0%';clearInterval(timer);timer=setInterval(async()=>{let j=await api('/api/job/'+r.job_id);bar.style.width=(j.progress*100)+'%';status.textContent=j.message;if(j.done){clearInterval(timer);load();if(j.run_id)showRun(j.run_id)}},750)}load();</script>'''

def rows(sql, params=()):
    if not DB.exists(): return []
    con=duckdb.connect(str(DB),read_only=True)
    try:return con.execute(sql,params).fetchall()
    finally:con.close()

def monitor(job_id,proc,expected):
    job=JOBS[job_id]
    raw_dir=ROOT/'evaluation'/'results'/'raw'/job['run_id']
    while proc.poll() is None:
        job['completed']=len(list(raw_dir.glob('*.json'))) if raw_dir.exists() else 0
        time.sleep(.5)
    job['done']=True;job['failed']=proc.returncode!=0
    job['completed']=expected if not job['failed'] else job['completed']

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def send_json(self,obj):
        data=json.dumps(obj,ensure_ascii=False).encode();self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':
            data=HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        if path=='/api/runs':return self.send_json([dict(zip(['run_id','dataset_version','started_at'],r)) for r in rows('select run_id,dataset_version,started_at from benchmark_runs order by started_at desc limit 30')])
        if path.startswith('/api/job/'):
            job=JOBS.get(path.rsplit('/',1)[-1],{});done=job.get('done',False);completed=job.get('completed',0);expected=max(job.get('expected',1),1);return self.send_json({'done':done,'run_id':job.get('run_id'),'progress':1 if done else min(completed/expected,.95),'message':'Failed — see terminal output' if job.get('failed') else ('Completed' if done else f'Running: {completed}/{expected} cases')})
        p=path.split('/')
        if len(p)==4 and p[2]=='run':
            sql="""select c.case_id,c.agent_version,c.status,c.latency_ms,coalesce(bool_and(s.passed),false),count(s.evaluator),coalesce(sum(case when s.passed then 1 else 0 end),0) from case_results c left join scores s using(run_id,case_id,agent_version) where c.run_id=? group by all order by c.case_id,c.agent_version""";cols=['case_id','agent_version','status','latency_ms','resolved','total_checks','passed_checks'];return self.send_json({'results':[dict(zip(cols,r)) for r in rows(sql,[p[3]])]})
        if len(p)==6 and p[2]=='trace':
            events=rows('select step,timestamp,type,name,input_json,output_json,success,duration_ms,metadata_json from trace_events where run_id=? and case_id=? and agent_version=? order by step',p[3:]);scores=rows('select evaluator,passed,details_json from scores where run_id=? and case_id=? and agent_version=?',p[3:]);return self.send_json({'events':[{'step':r[0],'timestamp':r[1],'type':r[2],'name':r[3],'input':json.loads(r[4]or'null'),'output':json.loads(r[5]or'null'),'success':r[6],'duration_ms':r[7],'metadata':json.loads(r[8]or'{}')}for r in events],'scores':[{'evaluator':r[0],'passed':r[1],'details':json.loads(r[2]or'{}')}for r in scores]})
        self.send_error(404)
    def do_POST(self):
        if self.path!='/api/benchmark':return self.send_error(404)
        body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))));agents=body.get('agents',['stack-v1.1']);dataset=body.get('dataset','core_v1');workers=str(body.get('workers',1));job_id=uuid.uuid4().hex;run_id=f"ui_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{job_id[:6]}_{dataset}";cmd=[sys.executable,'evaluation/benchmark.py',*(['--stack',agents[0]] if len(agents)==1 else ['--stacks',*agents]),'--dataset',dataset,'--workers',workers,'--run-id',run_id];proc=subprocess.Popen(cmd,cwd=ROOT);JOBS[job_id]={'run_id':run_id,'expected':5*len(agents),'completed':0,'done':False};threading.Thread(target=monitor,args=(job_id,proc,5*len(agents)),daemon=True).start();self.send_json({'job_id':job_id})

if __name__=='__main__':
    print('HeatScope Evaluation Dashboard: http://127.0.0.1:8844')
    ThreadingHTTPServer(('127.0.0.1',8844),Handler).serve_forever()
