# HeatScope project release management

HeatScope is versioned along independent tracks so a visual rollback cannot
silently change the Agent's reasoning policy or spatial data pipeline.

## Version tracks

| Track | Owns | Current release |
|---|---|---|
| Project | Runnable release composition and deployment record | `project-v1.2.1` |
| App | Map workspace, tool runtime and data loading | `app-v1.2.1` |
| UI | Presentation and interaction | `ui-v1.2.1` |
| Agent | Prompt, routing, tool policy and evidence constraints | `agent-v1.2.1` |
| Evaluator | Benchmark scoring rules and score meanings | `evaluator-v1.0.0` |
| Data | Source datasets, schema and derived assets | managed by dataset metadata and rebuild scripts |

## Current release matrix

| Component | Version | Git reference | Notes |
|---|---|---|---|
| UI | v1.1.0 | `ui-v1.1.0` / `d31f232` | Current HeatScope visual redesign. |
| Agent | v1.1.0 | `agent-v1.1.0` / `657f9bc` | Intent Gateway, allowlists and deterministic Evidence check. |
| Original Agent/UI baseline | v1.0.0 | `e866dc8` | Prompt-routed Agent and original visual baseline. |
| Integrated main build | v1.2.0 | `project-v1.2.0` | Administrative boundaries, editable RF scenario charts, and the chart-aware Intent Gateway. |
| Integrated release patch | v1.2.1 | `project-v1.2.1` | Registers the included ward and town GeoJSON as operational map layers. |

## Release procedure

1. Keep UI, Agent and data changes in separate commits where possible.
2. Update the relevant version metadata and its management document.
3. Run focused tests and verify the map UI when UI files change.
4. Create the matching annotated tag (`ui-v…`, `agent-v…` or `project-v…`).
5. Push branch and tags to GitHub.
6. For the production server, create a timestamped file backup, deploy only
   the approved files, restart the affected service and record the deployed
   component versions. Do not use `git pull` against its dirty worktree.

## Deployment record format

```text
Date:
Project tag / commit:
UI tag:
Agent tag:
Files deployed:
Server backup path:
Verification:
```

The server's Git HEAD may not match its file-deployed runtime. The deployment
record is therefore the operational source of truth, while Git tags preserve
the reproducible source versions.
