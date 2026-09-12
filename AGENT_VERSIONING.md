# HeatScope Agent version management

This document versions the **Agent behaviour**, separately from the HeatScope
application UI, data and deployment state. A release describes the system
prompt, routing contract, tool permissions and result-evidence rules that were
active for a user turn.

## Releases

| Agent release | Git tag | Baseline commit | Behaviour |
|---|---|---|---|
| v1.0.0 | `agent-v1.0.0` | `e866dc8` | The LLM received the system prompt and full tool schemas, then independently interpreted the request, selected tools and wrote the final answer. There was no structured task frame, tool allowlist or result validator. |
| v1.1.0 | `agent-v1.1.0` | `168d7a2` | Adds the Intent Gateway, a validated Task Frame, intent-specific tool allowlists and deterministic tool-result validation before the next LLM round. |

## What v1.1 adds

```text
User message
  -> Intent Gateway (LLM classification with deterministic fallback)
  -> Task Frame: status / intent / scope / allowed tools / constraints
  -> Agent tool loop
  -> deterministic Evidence check
  -> final LLM response grounded in tool output
```

The Evidence check is not an additional LLM prompt. It is code in
`app/intent-gateway.js` that marks failed, empty or explicitly unsuccessful
tool outputs. Its structured result is supplied to the next LLM round as a
system message.

## Release rules

- Patch version (`v1.1.1`): bug fix that does not change supported intents,
  tool permissions or answer constraints.
- Minor version (`v1.2.0`): adds or changes supported intents, prompt policy,
  tool allowlists, validation rules or visible Agent behaviour.
- Major version (`v2.0.0`): changes the Agent contract incompatibly.

For every Agent release:

1. Update `app/agent-version.js` and this table.
2. Run the relevant tests, including `node test/test_intent_gateway.mjs`.
3. Commit only Agent-related files.
4. Create an annotated Git tag, e.g. `git tag -a agent-v1.2.0 -m "Agent v1.2.0"`.
5. Push the branch and tag. Deployment notes must record both the app commit and
   Agent tag.

## Rollback

Use the Agent tag to restore the Agent implementation, rather than rolling
back unrelated map/UI/data changes. Server deployment remains file-based: first
back up the currently deployed Agent files, then deploy the files from the
selected tag and restart the web and MCP services.
