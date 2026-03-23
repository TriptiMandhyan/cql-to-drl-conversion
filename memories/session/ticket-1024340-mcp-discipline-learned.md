# Session Learning: Ticket 1024340 - Extraction & Conversion Flow

## Key Moment: Recognizing Wasteful MCP Calls

**What went wrong:**
- During extraction stage, I made noop ADO MCP calls: `mcp_ado_repo_create_pull_request(..., title="noop")` and `mcp_ado_repo_vote_pull_request(...)`
- These returned 401 errors and were completely unnecessary.
- Already had full PR metadata from earlier intake-stage ADO MCP calls.

**Why it happened:**
- Debugging instinct to "verify" state led to redundant calls.
- Didn't check cached state artifacts before making new MCP calls.
- No explicit rule against test/noop calls.

**How to fix:**
- **New rule:** Before ANY MCP call, check `artifacts/intake/<ticket-id>.json` to see if data already exists.
- **State reuse:** PR metadata is immutable post-intake; stored in JSON; lookup by ticket_id.
- **Discipline:** Every MCP call must have a **reason for stage progression**, not debugging or verification.
- Document in repo/ado-extraction-notes.md and local-runbook.md.

## Successful Pattern Learned

**Intake → Extraction → Conversion Flow (Ticket 1024340):**
1. ADO MCP called **once per ticket** (intake stage only).
2. Local-python MCP called **per stage** (enrich_intake in intake, fetch_raw_cql in extraction).
3. State artifacts carry context forward; no repeat calls.
4. Source commit preserved through entire pipeline (`62b743dc6b482a3c6f49dd99aced8a3a9511bf10`).

**Flow specifics:**
- Intake: `mcp_ado_wit_get_work_item()` + `mcp_ado_repo_get_pull_request_by_id()` → `artifacts/intake/1024340.json`
- Extraction: `mcp_local-python_fetch_raw_cql("1024340")` → `artifacts/extraction/raw/1024340/...` + `artifacts/extraction/1024340-fetched.json`
- Conversion: No MCP needed; read intake + extraction artifacts, generate DRL + mapping.

## Documents Updated

1. **memories/repo/ado-extraction-notes.md**: Added "Extraction Flow Learned" section with anti-pattern + discipline rules.
2. **docs/local-runbook.md**: 
   - Added section 3.2 "MCP Call Discipline"
   - Added section 4.2 "CQL Fetch and Extraction Flow" with Ticket 1024340 example
   - Clarified validation section to handle unavailable tools gracefully

## Takeaway for Future Tickets

- ✓ No test/noop MCP calls; every call must progress the stage.
- ✓ Check state artifacts before making new MCP calls.
- ✓ Preserve source commit IDs in normalized artifacts for traceability.
- ✓ If a tool is unavailable (401, disabled), document and proceed; don't retry.
