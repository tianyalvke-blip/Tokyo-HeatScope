/* Headless adapter around the existing browser Agent. No hidden reasoning is collected. */
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { performance } from 'node:perf_hooks';
import { Agent } from '../app/agent.js';

const request = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const now = () => new Date().toISOString();

class Collector {
  constructor() { this.trace = []; this.raw_trace = []; }
  record(type, name = null, input = null, output = null, success = null, duration_ms = null, metadata = {}) {
    this.trace.push({ step: this.trace.length + 1, timestamp: now(), type, name, input, output, success, duration_ms, metadata });
  }
  raw(type, payload) { this.raw_trace.push({ timestamp: now(), type, payload }); }
}

const localTools = new Set(['show_layer', 'hide_layer', 'set_filter', 'clear_filter', 'reset_filter', 'set_style', 'reset_style', 'set_tooltip', 'reset_tooltip', 'get_map_state', 'fly_to', 'geocode', 'list_datasets', 'get_schema', 'create_result_layer', 'remove_result_layer', 'list_result_layers', 'get_drawn_region']);
const knownTools = ['show_layer','hide_layer','set_filter','clear_filter','reset_filter','set_style','reset_style','set_tooltip','reset_tooltip','get_map_state','fly_to','geocode','list_datasets','get_schema','create_result_layer','remove_result_layer','list_result_layers','query','get_stac_details','create_sql_result','list_analysis_results','get_analysis_result','local_moran','rf_predict','run_python','search_policy_knowledge','filter_policy_interventions','get_policy_evidence'];
const definitions = knownTools.map(name => ({ type: 'function', function: { name, description: name, parameters: { type: 'object', properties: {}, additionalProperties: true } } }));

function bridgeTool(name, args) {
  return new Promise((resolve) => {
    const python = process.env.HEATSCOPE_PYTHON || (process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python');
    const child = spawn(python, ['evaluation/tool_bridge.py'], { cwd: process.cwd(), stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '', err = '';
    child.stdout.on('data', chunk => { out += chunk; }); child.stderr.on('data', chunk => { err += chunk; });
    child.on('error', error => resolve({ success: false, result: `TOOL_EXECUTION_ERROR: ${error.message}` }));
    child.on('close', () => {
      try { const data = JSON.parse(out); resolve(data.success ? { success: true, result: String(data.result) } : { success: false, result: data.error || 'TOOL_EXECUTION_ERROR' }); }
      catch { resolve({ success: false, result: `TOOL_EXECUTION_ERROR: ${err || out}` }); }
    });
    child.stdin.end(JSON.stringify({ name, args }));
  });
}

function fixtureResponse(query, gateway, tools) {
  const q = query.toLowerCase();
  if (gateway) {
    if (q.includes('tomorrow') || q.includes('明天')) return { content: JSON.stringify({ status: 'unsupported', intent: 'data_query', user_response: 'This system analyses LST and cannot predict tomorrow’s air temperature.', confidence: 1 }) };
    let intent = q.includes('policy') ? 'policy_lookup' : q.includes('predict') ? 'scenario_prediction' : q.includes('hotspot') ? 'hotspot_detection' : q.includes('show') ? 'map_display' : 'data_query';
    return { content: JSON.stringify({ status: 'supported', intent, spatial_scope: 'Tokyo 23 Wards', time_period: q.includes('day') ? 'daytime' : null, indicator: 'land_surface_temperature', method: intent === 'hotspot_detection' ? 'local_moran' : null, output: ['answer'], safety_notes: ['LST is not air temperature'], confidence: 1 }) };
  }
  if (tools.length === 0) return { content: 'Benchmark fixture final answer.' };
  let name = q.includes('policy') ? 'search_policy_knowledge' : q.includes('predict') ? 'rf_predict' : q.includes('hotspot') ? 'local_moran' : 'show_layer';
  let args = name === 'local_moran' ? { column: 'day_lst' } : name === 'rf_predict' ? { grid_id: 7191, model: 'day', overrides: { bldg_coverage_ratio: 0.3 } } : name === 'search_policy_knowledge' ? { query, top_k: 3 } : { layer_id: 'day_lst' };
  return { content: null, tool_calls: [{ id: `fixture_${Date.now()}`, type: 'function', function: { name, arguments: JSON.stringify(args) } }] };
}

async function main() {
  const collector = new Collector(); const started = performance.now();
  const manifest = request.manifest || {}; const live = Boolean(process.env.HEATSCOPE_LLM_ENDPOINT && process.env.HEATSCOPE_LLM_API_KEY);
  const config = { llm_models: [{ value: process.env.HEATSCOPE_LLM_MODEL || manifest.model || 'benchmark-fixture', endpoint: process.env.HEATSCOPE_LLM_ENDPOINT || 'https://fixture.invalid', api_key: process.env.HEATSCOPE_LLM_API_KEY || '' }], llm_model: process.env.HEATSCOPE_LLM_MODEL || manifest.model || 'benchmark-fixture', llm: { proxy: false }, temperature: manifest.temperature ?? 0, max_tool_calls: manifest.max_steps || 10, intent_gateway: { enabled: Boolean(manifest.intent_gateway), show_task_frame: true } };
  const registry = {
    getToolsForLLM(allowed = null) { const names = allowed === null ? null : new Set(allowed); return definitions.filter(item => !names || names.has(item.function.name)); },
    isLocal(name) { return localTools.has(name); },
    async execute(name, args) {
      const began = performance.now(); collector.record('tool_call', name, args, null, null, null, { source: localTools.has(name) ? 'local' : 'mcp' });
      let result;
      if (localTools.has(name)) result = { success: true, result: JSON.stringify({ success: true, action: name, args }), source: 'local' };
      else result = { ...(await bridgeTool(name, args)), source: 'remote', sqlQuery: args.sql_query || null };
      const duration = Math.round(performance.now() - began); const preview = String(result.result || '').slice(0, 800);
      collector.raw('tool_result', { name, args, result: result.result });
      collector.record('tool_result', name, null, { preview, chars: String(result.result || '').length }, result.success, duration, { source: result.source });
      if (localTools.has(name)) collector.record('map_action', name, args, null, result.success, duration);
      if (name === 'query' || name === 'create_sql_result') collector.record('sql_execution', name, { sql: args.sql_query }, { preview }, result.success, duration);
      if (name.includes('policy')) collector.record('rag_retrieval', name, args, { preview }, result.success, duration);
      return { name, ...result };
    }
  };
  const agent = new Agent(config, registry); agent.setSystemPrompt('You are the HeatScope benchmark agent. Use tools when useful and never claim LST is air temperature.');
  agent.onTaskFrame = frame => collector.record('router_decision', 'intent_gateway', { query: request.query }, frame, frame.status === 'supported');
  agent.onToolProposal = calls => { collector.record('planner_decision', 'tool_selection', { query: request.query }, { tools: calls.map(call => call.function.name) }, true); return { approved: true }; };
  agent.onValidation = validation => collector.record('validation', 'tool_results', null, validation, validation.status === 'valid');
  agent.onRetry = error => collector.record('retry', 'llm', null, { message: error.message }, false);
  if (!live) {
    let gatewayPending = Boolean(manifest.intent_gateway), toolIssued = false;
    agent.callLLM = async (_endpoint, _model, messages, tools) => {
      const began = performance.now(); let response;
      if (gatewayPending) { gatewayPending = false; response = fixtureResponse(request.query, true, []); }
      else if (!toolIssued && tools.length) { toolIssued = true; response = fixtureResponse(request.query, false, tools); }
      else response = { content: 'Benchmark fixture completed. Values are land surface temperature (LST), not air temperature.' };
      collector.record('llm_call', 'fixture', { message_count: messages.length, offered_tools: tools.map(tool => tool.function.name) }, { has_tool_calls: Boolean(response.tool_calls?.length) }, true, Math.round(performance.now() - began), { mode: 'fixture' }); return response;
    };
  } else {
    const original = agent.callLLM.bind(agent);
    agent.callLLM = async (endpoint, model, messages, tools) => { const began = performance.now(); try { const response = await original(endpoint, model, messages, tools); collector.record('llm_call', 'chat_completion', { message_count: messages.length, offered_tools: tools.map(tool => tool.function.name) }, { has_tool_calls: Boolean(response.tool_calls?.length) }, true, Math.round(performance.now() - began), { mode: 'live' }); return response; } catch (error) { collector.record('error', 'llm', null, { message: error.message }, false, Math.round(performance.now() - began), { code: 'MODEL_ERROR' }); throw error; } };
  }
  collector.record('user_input', 'user_query', { query: request.query }, null, true, 0);
  try {
    const output = await agent.processMessage(request.query);
    collector.record('final_answer', 'assistant', null, { text: output.response || '' }, !output.cancelled, 0);
    process.stdout.write(JSON.stringify({ run_id: `${Date.now()}`, case_id: request.case_id, agent_version: request.agent_version, final_answer: output.response || '', trace: collector.trace, raw_trace: collector.raw_trace, tool_calls: collector.trace.filter(e => e.type === 'tool_call'), tool_results: collector.trace.filter(e => e.type === 'tool_result'), map_actions: collector.trace.filter(e => e.type === 'map_action'), retrievals: collector.trace.filter(e => e.type === 'rag_retrieval'), latency_ms: Math.round(performance.now() - started), input_tokens: null, output_tokens: null, error: null, manifest }));
  } catch (error) {
    collector.record('error', 'agent', null, { message: error.message }, false, 0, { code: 'UNKNOWN' });
    process.stdout.write(JSON.stringify({ case_id: request.case_id, agent_version: request.agent_version, final_answer: '', trace: collector.trace, raw_trace: collector.raw_trace, tool_calls: [], tool_results: [], map_actions: [], retrievals: [], latency_ms: Math.round(performance.now() - started), input_tokens: null, output_tokens: null, error: error.message, manifest }));
  }
}
main();
