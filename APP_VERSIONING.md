# HeatScope App version management

The App version owns the common runtime: map workspace, local map tools, MCP
tool bridge, SQL/spatial-analysis server integration and data loading. It is
separate from UI presentation and Agent reasoning policy.

| App release | Git tag | Purpose |
|---|---|---|
| v1.0.0 | `app-v1.0.0` | Original application baseline at `e866dc8`. |
| v1.1.0 | `app-v1.1.0` | Current shared App runtime used by `stack-v1.0` and `stack-v1.1`. |

When a map tool, MCP tool, data-loading mechanism or spatial-analysis runtime
changes, create a new App release and add a new Stack manifest. A visual-only
change increments UI; a prompt/routing-only change increments Agent.
