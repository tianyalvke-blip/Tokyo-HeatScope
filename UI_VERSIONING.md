# HeatScope UI version management

UI releases govern the visual and interaction layer only: landing page,
map-workspace layout, responsive chat, colours, typography, legends and layer
controls. They do not change the Agent reasoning contract or analytical data.

## Releases

| UI release | Git tag | Baseline commit | Scope |
|---|---|---|---|
| v1.0.0 | `ui-v1.0.0` | `e866dc8` | Original visual baseline preserved before the current redesign. |
| v1.1.0 | `ui-v1.1.0` | `d31f232` | Current HeatScope visual redesign: landing experience, workspace styling and responsive interaction refinements. |
| v1.2.0 | `ui-v1.2.0` | pending this release | In-chat editable scenario charts: legend toggles, immediate Y-axis switching, baseline reference and direct NDVI axis values. |
| v1.2.1 | `ui-v1.2.1` | Makes the 23-ward boundary visible and the town-level boundary selectable in the map controls. |
| v1.2.2 | `ui-v1.2.2` | Replaces the three homepage PNGs with WebP (4.70 MB → 0.58 MB) and lazy-loads the two below-the-fold illustrations. |

## Rules

- Patch version: visual bug fix with no material workflow change.
- Minor version: new layout, navigation, page, visual system or user-facing
  interaction.
- Major version: a visual/workflow redesign that invalidates existing UI usage
  guidance.

For a UI release, update `app/ui-version.js`, this document and the combined
release matrix; test desktop and mobile views; then create and push an annotated
`ui-vX.Y.Z` tag. Keep UI commits separate from Agent policy and data changes.

## Rollback

To restore the original appearance while retaining current data, start from
`ui-v1.0.0` and selectively restore the UI files. Do not reset the whole
repository unless the intended rollback includes Agent and data changes too.
