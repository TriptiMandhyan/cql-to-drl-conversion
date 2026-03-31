# Agent Protocol (Adapted)

## Intent

Define shared behavior for all slash agents in this repository.

## Protocol

1. Resolve `ticketId` from `state/run-input.json`, then read `state/tickets/<ticket-id>/pipeline-status.json` before writing outputs.
2. Read stage input artifact from previous phase.
3. Write only stage-owned artifact files.
4. Update pipeline/approval state only through MCP state tools, not direct file edits.
5. Preserve ticket id, source refs, and source file paths.
6. If helper utilities are used, use them for fetch/IO only; keep policy decisions in agent instructions.
7. Use MCP tools exclusively for ADO metadata, content, and state operations:
   - `local-python.get_pr_changes(project_url, repository, pull_request_id)` for PR iteration changes (preferred over fallback scripts)
   - `local-python.enrich_intake` only for intake-stage `cqlPaths` enrichment
   - `local-python.fetch_raw_cql` only for extraction-stage commit-pinned raw CQL retrieval
   - `local-python.state_read_pipeline` and `local-python.state_read_approval` for state reads
   - `local-python.state_write_pipeline` and `local-python.state_write_approval` for state writes

## Guardrails

- Never proceed to PR submission when approval is false.
- Never treat approval from prior runs as valid for the current run; approval must be explicitly recorded in the current run by `/approvalRecorder` with approver identity provided at command time.
- Never use main branch when PR source refs are available.
- Never write secrets to artifacts.
- Mark unresolved logic as assumptions or blockers.
- Do not let helper scripts update stage transitions on behalf of the agent.
- Do not use helper scripts for extraction parsing, conversion, or PR submission stages.
- Do not use ad-hoc shell or PowerShell parsing commands (for example rg/grep/Select-String pipelines) as the primary stage logic when required artifacts are already local; use agent-native artifact reads and deterministic parsing in stage instructions.
- Do not use direct ADO REST URL calls from agent instructions when MCP tools are available. MCP transport is required.
- **MCP tool `local-python.get_pr_changes()` is the required path for PR metadata resolution. Never fall back to direct Python script execution for PR changes.**
- **All pipeline/approval state transitions must use `local-python.state_write_*` tools. Direct writes to state JSON files are not allowed.**
- Conversion outputs must use reference-style fact modeling (platform domain facts and minimal marker/helper declares).

## Stage Completion Gates

- Intake can complete only if `artifacts/intake/<ticket-id>.json` exists and `cqlPaths` is non-empty.
- Extraction can complete only if both `artifacts/extraction/<ticket-id>.json` and `artifacts/plan/<ticket-id>.md` exist and required raw CQL content was fetched for intake `cqlPaths`.
- Conversion can complete only if conversion artifacts are written for the current ticket.
- API artifact stage can complete only if `artifacts/pr-assets/<ticket-id>/<measure-slug>.json` exists.
- Test artifact stage can complete only if `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java` exists.
- Approval-recording stage can complete only if approval is explicitly written as true for the current run and pipeline stage is `pr-ready`.
- PR stage can complete only if approval is true for the current run and `artifacts/pr/<ticket-id>-pr.md` exists, then pipeline stage is set to `pr-submitted`.
