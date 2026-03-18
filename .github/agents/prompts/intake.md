# Intake Prompt Module

- Read ticket URL from `state/run-input.json`.
- Fetch ADO work item via MCP first; use PAT HTTPS fallback only if MCP is unavailable.
- Extract PR links and direct CQL source links from ticket description.
- Resolve source refs/commit ids from PR metadata when PR links exist.
- When PR links are absent, use branch/version data in direct CQL links and record missing commit ids as assumptions.
- Capture ticket URL, source refs, commit ids (when known), repo names, and CQL paths.
- Write `artifacts/intake/<ticket-id>.json`.
