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
loadTraces().then(run).catch(err => toast(`无法加载轨迹：${err.message}`));
