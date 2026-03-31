- Standard non-MCP fallback script: scripts/ado_fallback.py
- Preferred invocation: python scripts/ado_fallback.py enrich-intake --ticket-id <ticket-id>
- Helper scope is intake-stage MCP gaps only (latest PR iteration changed CQL paths).
- Extraction helper script: scripts/ado_extraction_fallback.py
- Preferred invocation via MCP: `mcp_local-python_fetch_raw_cql(ticket_id)` wraps the fallback script safely.
- Extraction helper scope is commit-pinned raw CQL retrieval only; parsing and stage transitions remain agent-owned.
- MCP remains first choice for ticket, PR, branch, and commit resolution.
- If MCP state writes fail with permission denied on state/tickets/index.json, verify it is a file (not a directory). The bootstrap in scripts/state_manager.py must create state/tickets directory, then write index.json.

## Extraction Flow Learned (Ticket 1024340)

**Proven pattern:**
1. Use ADO MCP only once per ticket: fetch work item, resolve PR metadata, capture source commit.
2. Pass source commit + changed CQL paths to local-python MCP `get_pr_changes()`.
3. Local-python MCP returns resolved cqlPaths list (no need to re-fetch PR; commit is already known).
4. Pass ticket_id to local-python MCP `fetch_raw_cql()` to retrieve commit-pinned CQL content.
5. Parse extracted CQL and generate normalized extraction artifact.

**Anti-pattern identified (Ticket 1024340 execution):**
- DO NOT call ADO MCP repeatedly to validate/re-check PR data.
- DO NOT make noop/test calls like `mcp_ado_repo_create_pull_request(..., title="noop")`.
- These calls waste tokens, hit 401 auth errors, and provide no new data.
- Once PR metadata is fetched (repo id, PR id, source commit), reuse that cached context.

**MCP call discipline:**
- **Before calling:** Ask "Do I already have this data from an earlier successful call?"
- **Re-use pattern:** Store PR metadata from intake → pass to extraction via ticket_id lookup → no repeat calls.
- **No test/noop calls:** Every MCP call must be necessary for stage progression; failures surface as actual errors, not as skippable.
- **Document tooling gaps:** If MCP operation is unavailable (e.g., `validate_conversion_artifacts`), note in pipeline state; don't attempt invalid calls.

## Reset Flow Lessons

- "Full reset" means more than stage rollback: remove ticket artifacts and ticket-scoped state so it resembles first-time ticket execution.
- Ticket-scoped state under `state/tickets/<ticket-id>/` is authoritative; singleton `state/pipeline-status.json` and `state/approval-status.json` are legacy/audit only.
- Reset must delete ticket artifacts: intake, extraction, extraction raw folder, plan, conversion mapping, PR draft, and ticket-generated DRL files.
- `state/tickets/index.json` must be a file; if it is a directory, reset/index updates fail and must be remediated explicitly.
- Reset execution discipline: use `local-python.state_reset_ticket_baseline(...)` as the primary path; do not default to shell cleanup.
- If MCP behavior does not reflect recent Python edits, restart `python scripts/local_mcp_server.py` before retrying tools.
- JSON reads in local MCP/state paths should be BOM-tolerant (`utf-8-sig`) to avoid parse failures on Windows-authored files.
- In this workspace setup, call `activate_pipeline_state_management_tools` before attempting `mcp_local-python_state_write_approval`; write tool may not be exposed until activation.
- Intake MCP nuance: `mcp_local-python_enrich_intake(ticket_id)` requires `resolvedPullRequests` in `artifacts/intake/<ticket-id>.json`; if missing, first resolve PR metadata via ADO MCP (`mcp_ado_wit_get_work_item` + `mcp_ado_repo_get_pull_request_by_id`) and write resolved PR entry, then enrich.
- Learning-agent fallback: if `state/run-input.json` lacks `learningStage`/`elapsedSeconds`, derive stage context from ticket pipeline status, map terminal stage `conversion-complete` to learning stage `conversion`, and record metrics with `elapsedSeconds=0` as non-blocking fallback.

