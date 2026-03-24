# Extraction Prompt Module

- Read `artifacts/intake/<ticket-id>.json`.
- Reuse PR metadata already persisted in intake `resolvedPullRequests`; only re-resolve via MCP if a required metadata field is missing.
- Use intake `cqlPaths` only; treat them as authoritative changed `.cql` paths.
- If intake `cqlPaths` is empty, stop and report blocker to intake stage.
- Read CQL file content from PR source commit using MCP tool `local-python.fetch_raw_cql(ticket_id)`.
- Verify raw CQL content exists for every required path in intake `cqlPaths`; if not, stop and report blockers.
- Extract definitions, includes, and terminology references in the agent stage using direct artifact reads, not ad-hoc terminal parsing scripts.
- Write `artifacts/extraction/<ticket-id>.json` with source file and commit traceability, and include blockers/assumptions when deterministic file resolution is not possible.
- Draft `artifacts/plan/<ticket-id>.md` from extraction output and `templates/plan-template.md`.
- Initialize `state/tickets/<ticket-id>/approval-status.json` with `approved=false`.
- Set `state/tickets/<ticket-id>/pipeline-status.json` to `awaiting-approval` using canonical values from `.github/orchestration/statuses.json` only after extraction and plan artifacts are present.
