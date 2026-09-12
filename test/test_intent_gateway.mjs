import assert from 'node:assert/strict';

import {
    allowedToolsForIntent,
    fallbackTaskFrame,
    normalizeTaskFrame,
    validateToolResults,
} from '../app/intent-gateway.js';
import { Agent } from '../app/agent.js';

const tools = [
    'show_layer', 'get_schema', 'query', 'local_moran', 'rf_predict',
    'run_python', 'search_policy_knowledge', 'get_policy_evidence',
];

{
    const frame = normalizeTaskFrame({
        status: 'supported',
        intent: 'hotspot_detection',
        spatial_scope: 'Shinjuku',
        indicator: 'land_surface_temperature',
        method: 'local_moran',
        output: ['map'],
        safety_notes: ['LST is not air temperature'],
        confidence: 1.2,
    }, '找出新宿白天热岛热点', tools);

    assert.equal(frame.status, 'supported');
    assert.equal(frame.intent, 'hotspot_detection');
    assert.equal(frame.confidence, 1);
    assert.deepEqual(frame.allowed_tools, ['show_layer', 'get_schema', 'query', 'local_moran']);
    assert.equal(frame.allowed_tools.includes('run_python'), false);
}

{
    const frame = normalizeTaskFrame({
        status: 'supported',
        intent: 'hotspot_detection',
        missing_fields: ['time_period'],
        confidence: 0.9,
    }, '找出新宿热点', tools);

    assert.equal(frame.status, 'needs_clarification');
    assert.deepEqual(frame.allowed_tools, []);
    assert.match(frame.user_response, /分析哪个区域、时段和指标/);
}

{
    const frame = normalizeTaskFrame({
        status: 'unsupported',
        intent: 'data_query',
        user_response: '当前数据不支持明天气温预测。',
        confidence: 0.98,
    }, '预测明天气温', tools);

    assert.deepEqual(frame.allowed_tools, []);
    assert.match(frame.user_response, /不支持/);
}

{
    assert.deepEqual(
        allowedToolsForIntent('scenario_prediction', tools),
        ['show_layer', 'get_schema', 'query', 'rf_predict'],
    );
}

{
    const fallback = fallbackTaskFrame('东京的热点在哪里？', tools, 'bad JSON');
    assert.equal(fallback.status, 'supported');
    assert.equal(fallback.intent, 'hotspot_detection');
    assert.equal(fallback.confidence, 0);
}

{
    const validation = validateToolResults([
        { name: 'query', success: true, source: 'remote', result: '42 rows' },
        { name: 'show_layer', success: false, source: 'error', result: 'not found' },
    ], { intent: 'data_query' });

    assert.equal(validation.status, 'needs_review');
    assert.deepEqual(validation.evidence, [{ tool: 'query', source: 'remote' }]);
    assert.deepEqual(validation.issues, [{ tool: 'show_layer', code: 'tool_failed' }]);
}

function mockRegistry() {
    const definitions = tools.map(name => ({
        type: 'function',
        function: { name, description: name, parameters: { type: 'object', properties: {} } },
    }));
    return {
        getToolsForLLM(allowed = null) {
            const names = allowed == null ? null : new Set(allowed);
            return definitions.filter(definition => names == null || names.has(definition.function.name));
        },
        isLocal() { return false; },
        has(name) { return tools.includes(name); },
        async execute() { throw new Error('No tool should execute in this test'); },
    };
}

{
    const agent = new Agent({
        llm_models: [{ value: 'test', endpoint: 'https://example.invalid' }],
        llm_model: 'test',
        intent_gateway: { enabled: true, show_task_frame: false },
    }, mockRegistry());
    agent.setSystemPrompt('test system prompt');

    const calls = [];
    const replies = [
        { content: JSON.stringify({
            status: 'unsupported',
            intent: 'data_query',
            user_response: '当前系统不支持明天气温预测。',
            confidence: 0.99,
        }) },
    ];
    agent.callLLM = async (_endpoint, _model, _messages, llmTools) => {
        calls.push(llmTools);
        return replies.shift();
    };

    const result = await agent.processMessage('预测明天气温');
    assert.equal(result.taskFrame.status, 'unsupported');
    assert.match(result.response, /不支持/);
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0], []);
}

{
    const agent = new Agent({
        llm_models: [{ value: 'test', endpoint: 'https://example.invalid' }],
        llm_model: 'test',
        intent_gateway: { enabled: true, show_task_frame: false },
    }, mockRegistry());
    agent.setSystemPrompt('test system prompt');

    const calls = [];
    const replies = [
        { content: JSON.stringify({
            status: 'supported',
            intent: 'hotspot_detection',
            spatial_scope: 'Shinjuku',
            indicator: 'land_surface_temperature',
            method: 'local_moran',
            safety_notes: ['LST is not air temperature'],
            confidence: 0.95,
        }) },
        { content: 'I would run the admitted hotspot workflow.' },
    ];
    agent.callLLM = async (_endpoint, _model, _messages, llmTools) => {
        calls.push(llmTools.map(tool => tool.function.name));
        return replies.shift();
    };

    const result = await agent.processMessage('找出新宿白天热点');
    assert.equal(result.taskFrame.status, 'supported');
    assert.equal(calls.length, 2);
    assert.deepEqual(calls[0], []);
    assert.equal(calls[1].includes('local_moran'), true);
    assert.equal(calls[1].includes('rf_predict'), false);
}

console.log('intent gateway tests passed');
