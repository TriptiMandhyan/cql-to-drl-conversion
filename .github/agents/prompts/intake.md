# Intake Prompt Module

- Read ticket URL from `state/run-input.json`.
- Fetch ADO work item via MCP first (ADO MCP tools); use PAT HTTPS fallback only if MCP is unavailable.
- Enforce guardrail `mcpPreferredForPrMetadata`: resolve PR metadata using MCP tool `local-python.get_pr_changes(project_url, repository, pull_request_id)` to fetch changed CQL files from each PR (never fall back to direct Python script execution).
- Write intake artifact once PR metadata is resolved.
- When intake `cqlPaths` is empty and PAT fallback is allowed, call MCP tool `local-python.enrich_intake(ticket_id)` to enrich changed CQL paths.
- Extract PR links and direct CQL source links from ticket description.
- Resolve source refs/commit ids from PR metadata when PR links exist (use `local-python.get_pr_changes` MCP tool for each PR).
- When PR links are absent, use branch/version data in direct CQL links and record missing commit ids as assumptions.
- Capture ticket URL, source refs, commit ids (when known), repo names, and CQL paths.
- Write `artifacts/intake/<ticket-id>.json`.
- **Do not fall back to direct Python execution. All PR changes must be fetched via `local-python.get_pr_changes` MCP tool.**
