/**
 * Agent release metadata.
 *
 * This is deliberately separate from the application version: an Agent release
 * describes its reasoning contract (prompt, routing policy and evidence rules),
 * so it can be compared or rolled back without guessing from a UI commit.
 */
export const CURRENT_AGENT_RELEASE = Object.freeze({
    version: '1.1.0',
    label: 'Intent Gateway',
    gitTag: 'agent-v1.1.0',
    implementationCommit: '168d7a2',
    releasedOn: '2026-09-12',
    capabilities: [
        'structured_task_frame',
        'tool_allowlist',
        'tool_result_validation',
        'evidence_constrained_answers',
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
