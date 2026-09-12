/**
 * Intent Gateway
 *
 * Converts an open-ended user message into a small, validated task frame before
 * the main agent sees any tools. The model proposes the frame; this module then
 * normalizes it and applies a code-owned tool allowlist so prompt output can
 * never expand its own permissions.
 */

export const TASK_STATUSES = Object.freeze([
    'supported',
    'needs_clarification',
    'unsupported',
    'unsafe_or_invalid',
]);

export const TASK_INTENTS = Object.freeze([
    'map_display',
    'data_query',
    'hotspot_detection',
    'comparison',
    'association_analysis',
    'scenario_prediction',
    'policy_lookup',
    'integrated_planning',
    'custom_analysis',
    'conversation_help',
]);

const MAP_TOOLS = [
    'show_layer', 'hide_layer', 'set_filter', 'clear_filter', 'reset_filter',
    'set_style', 'reset_style', 'set_tooltip', 'reset_tooltip', 'get_map_state',
    'fly_to', 'geocode', 'list_datasets', 'get_schema',
    'create_result_layer', 'remove_result_layer', 'list_result_layers',
];

const DATA_TOOLS = [
    'query', 'get_stac_details', 'create_sql_result',
    'list_analysis_results', 'get_analysis_result',
];

const POLICY_TOOLS = [
    'search_policy_knowledge', 'filter_policy_interventions', 'get_policy_evidence',
];

const TOOL_POLICY = Object.freeze({
    map_display: MAP_TOOLS,
    data_query: [...MAP_TOOLS, ...DATA_TOOLS],
    hotspot_detection: [...MAP_TOOLS, ...DATA_TOOLS, 'local_moran'],
    comparison: [...MAP_TOOLS, ...DATA_TOOLS],
    association_analysis: [...MAP_TOOLS, ...DATA_TOOLS, 'run_python'],
    scenario_prediction: [...MAP_TOOLS, ...DATA_TOOLS, 'rf_predict'],
    policy_lookup: [...MAP_TOOLS, ...POLICY_TOOLS],
    integrated_planning: [
        ...MAP_TOOLS, ...DATA_TOOLS, ...POLICY_TOOLS,
        'local_moran', 'rf_predict', 'run_python',
    ],
    custom_analysis: [...MAP_TOOLS, ...DATA_TOOLS, 'run_python'],
    conversation_help: [],
});

const GATEWAY_SYSTEM_PROMPT = `You are the request-admission layer for Urban HeatScope, a Tokyo urban-heat GeoAgent.

Classify the latest user message before the main agent receives tools. Return exactly one JSON object and no markdown.

Supported scope:
- Explore and map Tokyo 23-ward land surface temperature (LST) and available urban indicators.
- Query, summarize, compare, and map the supplied 200 m grid data.
- Detect spatial clusters/hotspots with Local Moran's I.
- Explore statistical associations without causal claims.
- Run RF urban-form what-if predictions for LST.
- Retrieve planning and heat-policy evidence from the installed knowledge base.
- Explain how to use this HeatScope application.

Scientific and operational boundaries:
- LST is land surface temperature, not air temperature.
- Do not promise weather forecasts or future air-temperature prediction.
- Do not accept requests that require unavailable datasets, places outside the loaded Tokyo scope, destructive actions, credential access, or unsupported causal proof.
- A vague but answerable request may use the documented default dataset. Ask one clarification only when a missing choice would materially change the analysis.
- Greetings and product-help questions are supported as conversation_help and require no tools.

Allowed intent values:
map_display, data_query, hotspot_detection, comparison, association_analysis,
scenario_prediction, policy_lookup, integrated_planning, custom_analysis, conversation_help.

Allowed status values:
- supported: the request can proceed.
- needs_clarification: one essential field is missing or ambiguous.
- unsupported: outside product/data/tool scope.
- unsafe_or_invalid: requests invalid scientific claims, destructive behavior, secrets, or unbounded execution.

Required JSON shape:
{
  "status": "supported",
  "intent": "hotspot_detection",
  "spatial_scope": "Shinjuku",
  "time_period": "daytime",
  "indicator": "land_surface_temperature",
  "method": "local_moran",
  "output": ["map", "summary", "method_note"],
  "missing_fields": [],
  "safety_notes": ["LST is not air temperature", "No causal claims"],
  "user_response": "",
  "confidence": 0.95
}

For needs_clarification, unsupported, or unsafe_or_invalid, user_response must be a concise, helpful response in the user's language. For needs_clarification it must contain exactly one focused question. For supported, user_response must be empty.`;

function asText(value) {
    return typeof value === 'string' ? value.trim() : '';
}

function asStringArray(value) {
    return Array.isArray(value)
        ? value.filter(item => typeof item === 'string').map(item => item.trim()).filter(Boolean)
        : [];
}

function clampConfidence(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.max(0, Math.min(1, number));
}

function defaultResponse(status, userMessage) {
    const zh = /[\u3400-\u9fff]/.test(userMessage || '');
    if (status === 'needs_clarification') {
        return zh
            ? '为了选择正确的数据和分析方法，你希望分析哪个区域、时段和指标？'
            : 'Which area, time period, and indicator should I analyze?';
    }
    if (status === 'unsafe_or_invalid') {
        return zh
            ? '这个请求超出了当前系统可安全、可靠执行的范围；我可以改为分析东京现有 LST 数据、统计关联或规划情景。'
            : 'That request is outside what this system can execute safely and reliably; I can instead analyze the available Tokyo LST data, associations, or planning scenarios.';
    }
    return zh
        ? '当前系统只支持东京现有地表温度、城市指标、空间分析、RF 情景和政策知识；你可以把问题改写为这些范围内的分析。'
        : 'This system supports the available Tokyo land-surface-temperature data, urban indicators, spatial analysis, RF scenarios, and policy knowledge. Please reframe the request within that scope.';
}

function heuristicIntent(userMessage) {
    const text = (userMessage || '').toLowerCase();
    if (/政策|规划指引|指南|法规|policy|guideline|citation|依据/.test(text)) return 'policy_lookup';
    if (/如果|情景|模拟|预测|增加.*绿|减少.*建筑|what\s*if|scenario|predict/.test(text)) return 'scenario_prediction';
    if (/热点|冷点|聚集|莫兰|moran|hot\s*spot|cold\s*spot|cluster/.test(text)) return 'hotspot_detection';
    if (/比较|对比|差异|compare|versus|\bvs\b/.test(text)) return 'comparison';
    if (/为什么|原因|影响因素|关联|相关|why|association|correlation/.test(text)) return 'association_analysis';
    if (/显示|隐藏|地图|图层|缩放|定位|show|hide|map|layer|zoom|fly/.test(text)) return 'map_display';
    if (/多少|平均|最高|最低|统计|计算|how many|average|highest|lowest|summar/.test(text)) return 'data_query';
    if (/^(你好|您好|hi|hello|help|怎么用|你能做什么)/.test(text.trim())) return 'conversation_help';
    return null;
}

function extractJsonObject(content) {
    if (typeof content !== 'string') throw new Error('Intent gateway returned no text');
    const withoutFence = content.replace(/^\s*```(?:json)?\s*/i, '').replace(/\s*```\s*$/i, '').trim();
    const start = withoutFence.indexOf('{');
    const end = withoutFence.lastIndexOf('}');
    if (start < 0 || end <= start) throw new Error('Intent gateway returned invalid JSON');
    return JSON.parse(withoutFence.slice(start, end + 1));
}

export function allowedToolsForIntent(intent, availableToolNames) {
    const policy = new Set(TOOL_POLICY[intent] || []);
    return [...new Set(availableToolNames || [])].filter(name => policy.has(name));
}

export function normalizeTaskFrame(raw, userMessage, availableToolNames) {
    const proposedStatus = asText(raw?.status);
    const proposedIntent = asText(raw?.intent);
    const missingFields = asStringArray(raw?.missing_fields);
    let status = TASK_STATUSES.includes(proposedStatus) ? proposedStatus : 'unsupported';
    // A frame cannot both be admitted and declare an essential missing input.
    // Downgrade it deterministically instead of hoping the planner notices.
    if (status === 'supported' && missingFields.length > 0) status = 'needs_clarification';
    const fallbackIntent = heuristicIntent(userMessage) || 'conversation_help';
    const intent = TASK_INTENTS.includes(proposedIntent) ? proposedIntent : fallbackIntent;
    const allowedTools = status === 'supported'
        ? allowedToolsForIntent(intent, availableToolNames)
        : [];

    return {
        status,
        intent,
        spatial_scope: asText(raw?.spatial_scope) || null,
        time_period: asText(raw?.time_period) || null,
        indicator: asText(raw?.indicator) || null,
        method: asText(raw?.method) || null,
        output: asStringArray(raw?.output),
        missing_fields: missingFields,
        safety_notes: asStringArray(raw?.safety_notes),
        user_response: status === 'supported'
            ? ''
            : (asText(raw?.user_response) || defaultResponse(status, userMessage)),
        confidence: clampConfidence(raw?.confidence),
        allowed_tools: allowedTools,
    };
}

export function fallbackTaskFrame(userMessage, availableToolNames, reason = '') {
    const intent = heuristicIntent(userMessage);
    if (!intent) {
        return normalizeTaskFrame({
            status: 'unsupported',
            intent: 'conversation_help',
            safety_notes: reason ? [`Gateway fallback: ${reason}`] : [],
            confidence: 0,
        }, userMessage, availableToolNames);
    }
    return normalizeTaskFrame({
        status: 'supported',
        intent,
        safety_notes: reason ? [`Gateway fallback: ${reason}`] : [],
        confidence: 0,
    }, userMessage, availableToolNames);
}

export function taskFrameInstruction(frame) {
    return `VALIDATED TASK FRAME\n${JSON.stringify(frame)}\n`
        + 'Use only allowed_tools. Treat missing fields and safety_notes as hard constraints. '
        + 'Do not broaden the request or claim access to unavailable data. Before the final answer, '
        + 'verify that every numerical or map claim is supported by returned tool evidence.';
}

export function validateToolResults(results, frame) {
    const issues = [];
    const evidence = [];

    for (const result of results || []) {
        const text = typeof result?.result === 'string' ? result.result.trim() : '';
        if (!result?.success || result?.source === 'error') {
            issues.push({ tool: result?.name || 'unknown', code: 'tool_failed' });
            continue;
        }
        if (!text) {
            issues.push({ tool: result?.name || 'unknown', code: 'empty_result' });
            continue;
        }
        let parsed = null;
        try { parsed = JSON.parse(text); } catch { /* many MCP tools return text/markdown */ }
        if (parsed && parsed.success === false) {
            issues.push({ tool: result?.name || 'unknown', code: 'reported_failure' });
            continue;
        }
        evidence.push({ tool: result?.name || 'unknown', source: result?.source || 'unknown' });
    }

    return {
        status: issues.length ? 'needs_review' : 'valid',
        intent: frame?.intent || null,
        issues,
        evidence,
        instruction: issues.length
            ? 'Do not treat failed or empty outputs as evidence. Correct the call if possible; otherwise explain the limitation.'
            : 'Use only the returned evidence and preserve the task-frame safety constraints.',
    };
}

export class IntentGateway {
    constructor(config = {}) {
        this.enabled = config.enabled !== false;
    }

    async classify({ userMessage, recentMessages = [], availableToolNames = [], request }) {
        if (!this.enabled) {
            return fallbackTaskFrame(userMessage, availableToolNames, 'disabled');
        }

        const history = recentMessages
            .slice(-4)
            .map(message => `${message.role}: ${String(message.content || '').slice(0, 500)}`)
            .join('\n');
        const userContent = `Available tool names: ${availableToolNames.join(', ') || '(none)'}\n`
            + `${history ? `Recent conversation:\n${history}\n\n` : ''}`
            + `Latest user message:\n${userMessage}`;

        try {
            const message = await request([
                { role: 'system', content: GATEWAY_SYSTEM_PROMPT },
                { role: 'user', content: userContent },
            ]);
            return normalizeTaskFrame(extractJsonObject(message?.content), userMessage, availableToolNames);
        } catch (error) {
            if (error?.name === 'AbortError') throw error;
            console.warn('[IntentGateway] Falling back to deterministic routing:', error);
            return fallbackTaskFrame(userMessage, availableToolNames, error?.message || 'classification failed');
        }
    }
}
