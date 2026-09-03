const $ = (id) => document.getElementById(id);
let report = null;

function toast(message) {
  const el = $('toast'); el.textContent = message; el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2400);
}

function render() {
  if (!report) return;
  const s = report.summary;
  $('summaryCards').innerHTML = [
    ['通过率', `${(s.pass_rate * 100).toFixed(1)}%`, s.pass_rate === 1 ? 'good' : 'bad'],
    ['通过用例', `${s.passed} / ${s.total}`, s.passed === s.total ? 'good' : ''],
    ['失败用例', `${s.total - s.passed}`, s.total - s.passed ? 'bad' : 'good'],
    ['轨迹文件', report.traces_file.split(/[\\/]/).pop(), 'muted'],
  ].map(([label, value, cls]) => `<div class="card"><div class="label">${label}</div><div class="value ${cls}">${escapeHtml(value)}</div></div>`).join('');
  $('sourceLabel').textContent = `${report.cases_file.split(/[\\/]/).pop()} · ${report.traces_file.split(/[\\/]/).pop()}`;
  $('categoryBars').innerHTML = Object.entries(report.by_category).map(([name, x]) => {
    const rate = x.total ? x.passed / x.total : 0;
    return `<div class="bar-row"><strong>${escapeHtml(name)}</strong><div class="bar"><i style="width:${rate * 100}%"></i></div><span>${x.passed}/${x.total}</span></div>`;
  }).join('');
  renderRows();
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
  $('jsonLink').href = URL.createObjectURL(blob);
}

function renderRows() {
  const filter = $('statusFilter').value;
  const rows = report.results.filter(x => filter === 'all' || (filter === 'passed' ? x.passed : !x.passed));
  $('resultsBody').innerHTML = rows.map(x => `<tr>
    <td><span class="pill ${x.passed ? 'pass' : 'fail'}">${x.passed ? '通过' : '失败'}</span></td>
    <td><code>${escapeHtml(x.id)}</code></td><td>${escapeHtml(x.category)}</td>
    <td>${(x.actual_tools || []).map(t => `<code>${escapeHtml(t)}</code>`).join(' → ') || '<span class="muted">无工具</span>'}</td>
    <td>${x.latency_ms == null ? '—' : `${x.latency_ms} ms`}</td>
    <td class="reason">${escapeHtml((x.failures || []).join('\n')) || '—'}</td>
  </tr>`).join('');
}

function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function loadTraces() {
  const data = await fetch('/api/traces').then(r => r.json());
  $('traceSelect').innerHTML = data.traces.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
}

async function loadCases() {
  const suite = $('suiteSelect').value;
  const data = await fetch(`/api/cases?suite=${encodeURIComponent(suite)}`).then(r => r.json());
  $('caseSelect').innerHTML = data.cases.map(x => `<option value="${escapeHtml(x.id)}">${escapeHtml(x.id)} · ${escapeHtml(x.label.slice(0, 100))}</option>`).join('');
}

async function openAgent() {
  const suite = $('suiteSelect').value;
  const id = $('caseSelect').value;
  const data = await fetch(`/api/cases?suite=${encodeURIComponent(suite)}`).then(r => r.json());
  const item = data.cases.find(x => x.id === id);
  if (!item) return toast('找不到测试用例');
  const prompt = item.label.split(' / ')[0];
  // Same-tab navigation is reliable in the embedded browser and keeps this a
  // true one-click entry point. The browser Back button returns to the panel.
  window.location.href = `http://127.0.0.1:8100/?eval_prompt=${encodeURIComponent(prompt)}`;
}

function runRealSuite() {
  const suite = $('suiteSelect').value;
  const label = suite === 'multiturn' ? 'Multi-turn（20 组）' : suite === 'core' ? 'Core（60 题）' : 'Golden（31 题）';
  if (!confirm(`将使用当前浏览器中保存的 API Key 执行 ${label}，确定继续吗？`)) return;
  const target = `http://127.0.0.1:8100/?eval_suite=${encodeURIComponent(suite)}`;
  const opened = window.open(target, '_blank', 'noopener');
  if (!opened) toast('浏览器阻止了新标签页，请允许弹窗后重试');
}

async function pollRealStatus() {
  try {
    const s = await fetch('http://127.0.0.1:8170/api/real-status', { cache: 'no-store' }).then(r => r.json());
    const total = Number(s.total || 0), completed = Number(s.completed || 0);
    $('liveStatus').textContent = s.state === 'running' ? `${completed}/${total}` : (s.state === 'done' ? '已完成' : '未运行');
    $('liveProgressBar').style.width = total ? `${Math.min(100, completed / total * 100)}%` : '0%';
    $('liveMessage').textContent = s.message || (s.current ? `当前：${s.current}` : '点击“运行整套真实 Agent”后，这里会实时显示进度。');
  } catch (_) { /* dashboard may be opened before the API is ready */ }
}

async function run() {
  $('runBtn').disabled = true; $('runBtn').textContent = '评测中…';
  try {
    const trace = encodeURIComponent($('traceSelect').value);
    const response = await fetch(`/api/evaluate?trace=${trace}`);
    report = await response.json();
    if (report.error) throw new Error(report.error);
    render(); toast(`评测完成：${report.summary.passed}/${report.summary.total} 通过`);
  } catch (err) { toast(`评测失败：${err.message}`); }
  finally { $('runBtn').disabled = false; $('runBtn').textContent = '运行评测'; }
}

$('runBtn').addEventListener('click', run); $('statusFilter').addEventListener('change', renderRows);
$('suiteSelect').addEventListener('change', () => loadCases().catch(err => toast(`无法加载用例：${err.message}`)));
$('openAgentBtn').addEventListener('click', openAgent);
$('runRealBtn').addEventListener('click', runRealSuite);
Promise.all([loadTraces(), loadCases()]).then(run).catch(err => toast(`无法加载评测数据：${err.message}`));
setInterval(pollRealStatus, 1000); pollRealStatus();
