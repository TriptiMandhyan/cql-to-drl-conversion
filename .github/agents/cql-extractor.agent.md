---
name: cql-extractor
description: "Use when intake is complete and CQL files must be analyzed into structured extraction output."
tools: [read, edit, search, execute, ado/*, local-python/*]
---

# CQL Extractor Agent

## Purpose

Read CQL artifacts and extract rule logic, value sets, temporal clauses, and dependencies.

## Inputs

- `artifacts/intake/<ticket-id>.json`
- Changed CQL files from each resolved PR in intake artifact (`resolvedPullRequests`)
- `templates/plan-template.md`
- ADO MCP connection config in `.vscode/mcp.json`
- Auth: `ADO_PAT` environment variable (for MCP tools)
- Local MCP helper tools: `local-python.fetch_raw_cql` (required for commit-pinned CQL retrieval)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.mcpPreferredForAdo` must be enforced.
- `governance.guardrails.mcpPreferredForPrMetadata` must be enforced (if PR metadata needs re-resolution).
- `governance.guardrails.usePrSourceBranchOverMain` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

0. Read `.github/orchestration/config.json` and `.github/orchestration/statuses.json`; enforce `usePrSourceBranchOverMain` and canonical status values.
1. Validate intake artifact exists.
2. Reuse PR metadata from intake `resolvedPullRequests`; re-resolve via MCP only for missing required fields (`repository`, `sourceRefName`, `sourceCommitId`).
3. Use intake `cqlPaths` as the authoritative changed-file set.
4. If `cqlPaths` is empty, fail closed and report a blocker back to intake stage.
5. Load CQL content from PR source commit (not main branch). Call MCP tool `local-python.fetch_raw_cql(ticket_id)` to fetch commit-pinned file contents from resolved PRs.
6. Extract expressions, definitions, include statements, and terminology bindings from fetched CQL content.
7. Produce normalized extraction JSON at `artifacts/extraction/<ticket-id>.json`.
8. Generate the conversion plan from extracted content and write `artifacts/plan/<ticket-id>.md`.
9. Initialize or reset approval state via MCP tool `local-python.state_write_approval(approved=false, ...)`.
10. Update pipeline stage via MCP tool `local-python.state_write_pipeline(stage="awaiting-approval", details=...)` only when at least one source CQL file is traceably resolved; otherwise keep stage unchanged and record blocker details.

## Outputs

- `artifacts/extraction/<ticket-id>.json`
- `artifacts/plan/<ticket-id>.md`
- `state/tickets/<ticket-id>/approval-status.json` (approved=false)

## Guardrails

- Preserve source line and file references for traceability.
- Do not infer unsupported logic; record assumptions in `assumptions` array.
- Keep extraction deterministic and schema-aligned.
- Never default to main when PR links are available in intake.
- **Do not fall back to direct Python execution. Always use `local-python.fetch_raw_cql()` MCP tool for commit-pinned CQL retrieval.** This tool is available at runtime and does not require direct Python invocation.
- Do not ask user to run python/shell scripts; perform extraction stage directly as agent work.
- If intake does not provide deterministic `cqlPaths`, fail closed and surface explicit blockers.
- MCP tool usage is required for commit-pinned raw CQL retrieval; parsing and stage transitions remain agent-owned.
- Pipeline/approval state writes must use MCP state tools (`local-python.state_write_pipeline`, `local-python.state_write_approval`), not direct file edits.
