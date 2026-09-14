/**
 * Agent release metadata.
 *
 * This is deliberately separate from the application version: an Agent release
 * describes its reasoning contract (prompt, routing policy and evidence rules),
 * so it can be compared or rolled back without guessing from a UI commit.
 */
export const CURRENT_AGENT_RELEASE = Object.freeze({
    version: '1.2.2',
    label: 'Intent Gateway with default response curves',
    gitTag: 'agent-v1.2.2',
    implementationCommit: 'project-v1.2.3',
    releasedOn: '2026-09-14',
    capabilities: [
        'structured_task_frame',
        'tool_allowlist',
        'tool_result_validation',
        'evidence_constrained_answers',
        'chart_edit_intent',
        'chart_aware_runtime_context',
        'default_counterfactual_response_curves',
    ],
});

export const AGENT_RELEASE_HISTORY = Object.freeze([
    Object.freeze({
        version: '1.0.0',
        label: 'Prompt-routed Agent',
        gitTag: 'agent-v1.0.0',
        implementationCommit: 'e866dc8',
        releasedOn: '2026-09-10',
        capabilities: ['prompt_routing', 'llm_selected_tools'],
    }),
    CURRENT_AGENT_RELEASE,
]);
