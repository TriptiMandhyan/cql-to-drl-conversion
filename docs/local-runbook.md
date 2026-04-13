# Local Runbook

## 1) Create ADO PAT

In Azure DevOps:

1. Open User Settings > Personal access tokens.
2. Select New Token.
3. Set organization to `healthcatalyst` and a short expiry window.
4. Scopes minimum needed for this local flow:
	- Work Items: Read
	- Code: Read
5. Create token and copy it once.

## 2) Configure local secret

Set environment variable in your shell session:

```bash
export ADO_PAT="<pat>"
```

Windows persistent equivalent:

```text
setx ADO_PAT "<pat>"
```

## 3) Set ticket URL placeholder

Edit `state/run-input.json` and set:

- `ticketUrl`: `https://dev.azure.com/healthcatalyst/MeasureAble%202.0/_workitems/edit/1024330/`

The intake step will parse ticket description and resolve PR links such as:

- `https://dev.azure.com/healthcatalyst/MeasureAble%202.0/_git/measures/pullrequest/<pr-id>`

The workflow uses PR source branch refs, not main branch, when PR links are present.

## 3.1) MANDATORY: Start local FastAPI MCP server

Install dependencies:

```bash
python -m pip install -r config/mcp/requirements-local-mcp.txt
```

Run local MCP server:

```bash
python scripts/local_mcp_server.py
```

This process must be running before invoking slash agents that depend on local-python MCP tools.

If you change MCP/state code (for example `scripts/local_mcp_server.py` or `scripts/state_manager.py`), restart this process before making MCP calls.

The local MCP URL configured in `.vscode/mcp.json` is:

- `http://127.0.0.1:8765/mcp`

## 3.2) MCP Call Discipline (Lesson from Ticket 1024340)

**Golden rule:** Before calling any MCP tool, ask: "Do I already have this data from an earlier successful call in this conversation?"

**Anti-patterns to avoid:**
- Do NOT make test/noop MCP calls (e.g., `mcp_ado_repo_create_pull_request(..., title="noop")`).
- Do NOT re-call ADO MCP to re-validate PR data already fetched in intake.
- Do NOT make MCP calls without a clear reason for progress; unused calls waste tokens and surface as auth errors.

**Proven pattern (Ticket 1024340 intake-to-extraction):**
1. **Intake stage:** Use ADO MCP once:
   - `mcp_ado_wit_get_work_item(id)` → capture ticket URL, description, linked PR.
   - `mcp_ado_repo_get_pull_request_by_id(prId)` → capture PR source branch, source commit.
   - Store in `artifacts/intake/<ticket-id>.json` (persisted state).
2. **Extraction stage:** Use local-python MCP only:
   - `mcp_local-python_fetch_raw_cql(ticket_id)` → wraps script, uses stored PR commit, retrieves raw CQL files.
   - No need to re-call ADO MCP; ticket_id is the lookup key to all prior PR metadata.
3. **Why this works:** State artifacts (`intake/<ticket-id>.json`, `extraction/<ticket-id>-fetched.json`) carry forward all necessary context; MCP calls are unidirectional (fetch once, reuse context).

**Implementation check:**
-  Before any ADO MCP call outside intake: check if data already exists in `artifacts/intake/<ticket-id>.json`.
-  Before any local-python MCP call: check if `artifacts/intake/<ticket-id>.json` exists (required input).
-  If a tool is unavailable (returns disabled error or 401), document in pipeline state and proceed without it (don't retry noop calls).

## 4) Initialize ticket state directory

Before running agents, ensure the state directory structure exists. You can either:

**Option A: Use the initialization script (recommended)**

```powershell
python scripts/init_state_structure.py
```

This will:
- Create `state/tickets/` directory
- Create `state/tickets/index.json` (master index of all tickets)
- Create template `state/run-input.json` if missing

**Option B: Manual setup**

```powershell
# Create the tickets state folder if it doesn't exist
mkdir -p state/tickets
```

The folder structure created will be:

```
state/
  tickets/
    <ticket-id>/
      pipeline-status.json      (created by intake agent)
      approval-status.json      (created by extractor agent)
      history.json              (optional, created by agents)
    index.json                  (master index, maintains all ticket IDs and stages)
```

## 5) Execute stages with agents

Run stages from Copilot chat using slash agents:

1. `/ticketDescriptionIntakeAgent`
2. `/cql-extractor`
3. `/conversion`
4. `/semanticCheck`
5. `/apiArtifactBuilder`
6. `/testRunFileBuilder`
7. `/approvalRecorder` (single call with approver identity and optional note)
8. `/pr-submission`

## 5.1) Local MCP helper tools

When MCP is preferred but a stage needs HTTPS fallback for capabilities not currently exposed in ADO MCP, use these local MCP tools:

- `local-python.enrich_intake(ticket_id="<ticket-id>")`
- `local-python.get_pr_changes(project_url, repository, pull_request_id)`
- `local-python.fetch_raw_cql(ticket_id="<ticket-id>")`
- `local-python.state_read_pipeline(ticket_id?)` / `local-python.state_write_pipeline(...)`
- `local-python.state_read_approval(ticket_id?)` / `local-python.state_write_approval(...)`
- `local-python.state_reset_ticket_baseline(ticket_id, clear_legacy_singleton_state?)`

Reset policy:

- Use `local-python.state_reset_ticket_baseline(...)` as the primary and preferred reset mechanism.
- Do not use shell-based cleanup for ticket reset unless explicitly approved as a break-glass action.
- If reset reports JSON/BOM parsing failures, restart local MCP server first, then retry reset.
- Keep state JSON files UTF-8 clean; the local MCP/state readers are BOM-tolerant (`utf-8-sig`) for resilience.

Outputs:

- Updated `artifacts/intake/<ticket-id>.json` (`cqlPaths` enriched in place)
- Raw CQL files under `artifacts/extraction/raw/<ticket-id>/...`
- Fetch manifest at `artifacts/extraction/<ticket-id>-fetched.json`

Notes:

- `ADO_PAT` must be set in environment.
- `artifacts/intake/<ticket-id>.json` must exist.
- `enrich_intake` maps to `scripts/ado_fallback.py` and is intake-only for changed `.cql` path resolution.
- `fetch_raw_cql` maps to `scripts/ado_extraction_fallback.py` and is extraction-only for commit-pinned raw `.cql` retrieval.
- `state_*` tools map to `scripts/state_manager.py` and are required for state reads/writes.
- Neither helper parses CQL or updates pipeline state.

## 5.2) CQL Fetch and Extraction Flow (from Ticket 1024340)

**Prerequisite:** `artifacts/intake/<ticket-id>.json` must exist (written by intake stage).

**Flow:**
1. Call `local-python.fetch_raw_cql(ticket_id="<ticket-id>")` via MCP.
   - Returns: `{ "ok": true, "cqlPaths": [...], "fetched": N, "unresolvedPaths": [...] }`
   - Produces: `artifacts/extraction/raw/<ticket-id>/...` (raw CQL files)
   - Produces: `artifacts/extraction/<ticket-id>-fetched.json` (manifest with PR commit, raw file paths)
2. Parse fetched CQL files (via extraction agent or manual parse).
   - Extract: definitions (name, line), includes (library, alias, line), terminology (kind, name, line).
3. Write normalized extraction artifact.
   - File: `artifacts/extraction/<ticket-id>.json`
   - Content: sourceType, files[], definitions[], includes[], terminology[], assumptions, status=extraction-complete.
   - **Important:** Preserve source commit ID in extraction artifact for downstream conversion traceability.

**Example from Ticket 1024340:**
```json
{
  "ticketId": "1024340",
  "sourceType": "pr-changed-cql-files",
  "files": [{
    "prId": "109928",
    "repository": "measures",
    "path": "/measures/2026/MIPS/050.cql",
    "sourceCommitId": "62b743dc6b482a3c6f49dd99aced8a3a9511bf10",
    "definitions": [
      { "name": "Denominator", "line": 28 },
      { "name": "Denominator Exclusion G9694", "line": 55 }
    ],
    "includes": [
      { "library": "2026/MIPS/shared/sharedHospice.cql", "alias": "sharedHospice", "line": 11 }
    ],
    "terminology": [
      { "kind": "valueset", "name": "MIPS; 050_ENCOUNTER", "identifier": null, "line": 14 }
    ]
  }],
  "status": "extraction-complete"
}
```

**Why this pattern works:**
- ✓ Source commit is persisted in extraction artifact for DRL conversion reference.
- ✓ Extracted definitions (with line numbers) enable direct CQL-to-DRL rule mapping.
- ✓ No repeat ADO MCP calls; all PR metadata already in intake artifact.
- ✓ Raw CQL files available for offline review/validation.

### 5.2.1) When CQL is downloaded (and when it is not)

- CQL download happens in extraction only: `/cql-extractor` calls `local-python.fetch_raw_cql(ticket_id)`.
- The fetch is commit-pinned to the PR source commit stored in intake (`sourceCommitId`).
- On each extraction run, files are written to `artifacts/extraction/raw/<ticket-id>/...` and the fetch manifest is rewritten at `artifacts/extraction/<ticket-id>-fetched.json`.
- If the pipeline is already at `conversion-ready` or later, and you continue from that stage, extraction is not re-run, so no new CQL download occurs.

To force a fresh CQL download for the same ticket:
1. Run `/ticketStatusReset`.
2. Run `/ticketDescriptionIntakeAgent`.
3. Run `/cql-extractor`.

This guarantees intake metadata is refreshed and commit-pinned raw CQL is fetched again before conversion.

## 5.3) Approval gate

`/cql-extractor` writes extraction and plan artifacts and initializes approval to false.

Approval and pipeline status are ticket-scoped at:

- `state/tickets/<ticket-id>/approval-status.json`
- `state/tickets/<ticket-id>/pipeline-status.json`

`/approvalRecorder` performs one action only: record explicit human approval details and move pipeline to `pr-ready`.

## 6) Validate outputs

Check for generated files:

- `artifacts/conversion/<measure-slug>.drl`
- `artifacts/conversion/<ticket-id>-mapping.md`
- `artifacts/review/<ticket-id>-semantic-check.md`


Run conversion artifact validation via MCP tool (if available):

- `local-python.validate_conversion_artifacts(ticket_id="<ticket-id>")`

Validation checks naming, EMR fire-once guards, and reference-style fact modeling.

If the tool is disabled or unavailable, document in pipeline state (`details: "...validation tool unavailable..."`); do not retry noop calls.

For ticket `1024340`, expect:
- `artifacts/conversion/<measure-slug>.drl` (example: `ecqm050rate1.drl`)
- `artifacts/conversion/1024340-mapping.md`

