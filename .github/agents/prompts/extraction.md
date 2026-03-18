# Extraction Prompt Module

- Read `artifacts/intake/<ticket-id>.json`.
- For each resolved PR, resolve PR metadata first using MCP (`repository`, `sourceRefName`, `sourceCommitId`).
- Use MCP-available signals (`cqlPaths`, branch-scoped directory/search) to build candidate `.cql` paths.
- Accept MCP-only paths only when deterministic (single candidate). Do not infer when multiple candidates exist.
- For operations not currently available in MCP (latest PR iteration changed files, file content by commit/path), use PAT HTTPS fallback when allowed by config.
- Read CQL file content from PR source commit.
- Optional: use `scripts/run_extractor.py` to fetch raw CQL content only.
- Extract definitions, includes, and terminology references in the agent stage.
- Write `artifacts/extraction/<ticket-id>.json` with source file and commit traceability, and include blockers/assumptions when deterministic file resolution is not possible.
