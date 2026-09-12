/**
 * Visual release metadata.
 *
 * UI releases track presentation and interaction independently from the Agent
 * reasoning contract in agent-version.js.
 */
export const CURRENT_UI_RELEASE = Object.freeze({
    version: '1.1.0',
    label: 'HeatScope visual redesign',
    gitTag: 'ui-v1.1.0',
    implementationCommit: 'd31f232',
    releasedOn: '2026-09-11',
    scope: ['landing_page', 'map_workspace', 'responsive_chat', 'layer_controls'],
});

export const UI_RELEASE_HISTORY = Object.freeze([
    Object.freeze({
        version: '1.0.0',
        label: 'Original visual baseline',
        gitTag: 'ui-v1.0.0',
        implementationCommit: 'e866dc8',
        releasedOn: '2026-09-10',
    }),
    CURRENT_UI_RELEASE,
]);
