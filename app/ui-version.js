/**
 * Visual release metadata.
 *
 * UI releases track presentation and interaction independently from the Agent
 * reasoning contract in agent-version.js.
 */
export const CURRENT_UI_RELEASE = Object.freeze({
    version: '1.2.2',
    label: 'Homepage image-performance patch',
    gitTag: 'ui-v1.2.2',
    implementationCommit: 'project-v1.2.2',
    releasedOn: '2026-09-14',
    scope: ['landing_page', 'webp_images', 'lazy_loading'],
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
