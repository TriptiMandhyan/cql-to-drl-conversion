# Extraction Prompt Module

- Read `artifacts/intake/<ticket-id>.json`.
- For each resolved PR, resolve PR metadata first using MCP (`repository`, `sourceRefName`, `sourceCommitId`).
- Use intake `cqlPaths` only; treat them as authoritative changed `.cql` paths.
- If intake `cqlPaths` is empty, stop and report blocker to intake stage.
- Read CQL file content from PR source commit. If MCP cannot fetch commit-pinned file contents, use `scripts/ado_extraction_fallback.py fetch-raw-cql` for raw-file retrieval only.
- Extract definitions, includes, and terminology references in the agent stage.
- Write `artifacts/extraction/<ticket-id>.json` with source file and commit traceability, and include blockers/assumptions when deterministic file resolution is not possible.
