---
name: cql-extractor
description: "Use when intake is complete and CQL files must be analyzed into structured extraction output."
tools: [read, edit, search, execute, ado/*]
---

# CQL Extractor Agent

## Purpose

Read CQL artifacts and extract rule logic, value sets, temporal clauses, and dependencies.

## Inputs

- `artifacts/intake/<ticket-id>.json`
- Changed CQL files from each resolved PR in intake artifact (`resolvedPullRequests`)
- ADO MCP connection config in `.vscode/mcp.json`
- Fallback auth: `ADO_PAT` environment variable
- Fallback helper: `scripts/ado_extraction_fallback.py` (`fetch-raw-cql`)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.mcpPreferredForAdo` must be enforced.
- `governance.guardrails.usePrSourceBranchOverMain` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

0. Read `.github/orchestration/config.json` and enforce `usePrSourceBranchOverMain`.
1. Validate intake artifact exists.
2. Use ADO MCP connection first to resolve PR metadata (`repository`, `sourceRefName`, `sourceCommitId`) for each `resolvedPullRequests` entry.
3. Use intake `cqlPaths` as the authoritative changed-file set.
4. If `cqlPaths` is empty, fail closed and report a blocker back to intake stage.
5. Load CQL content from PR source commit (not main branch). If MCP cannot fetch commit-pinned file contents directly, use `scripts/ado_extraction_fallback.py fetch-raw-cql` for remote fetch only.
6. Extract expressions, definitions, include statements, and terminology bindings from fetched CQL content.
7. Produce normalized extraction JSON at `artifacts/extraction/<ticket-id>.json`.
8. Update `state/pipeline-status.json` stage to `extraction-complete` only when at least one source CQL file is traceably resolved; otherwise keep stage unchanged and record blocker details.

## Outputs

- `artifacts/extraction/<ticket-id>.json`

## Guardrails

- Preserve source line and file references for traceability.
- Do not infer unsupported logic; record assumptions in `assumptions` array.
- Keep extraction deterministic and schema-aligned.
- Never default to main when PR links are available in intake.
- Do not ask user to run python/shell scripts; perform extraction stage directly as agent work.
- If intake does not provide deterministic `cqlPaths`, fail closed and surface explicit blockers.
- Helper usage is limited to commit-pinned raw CQL retrieval and fetched-manifest output; parsing and stage transitions remain agent-owned.
