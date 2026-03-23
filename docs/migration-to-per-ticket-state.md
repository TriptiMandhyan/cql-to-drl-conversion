# Multi-Ticket State Management: Migration Guide

## Overview
This guide walks through migrating the architecture from **singleton state files** (one active ticket) to **per-ticket state directories** (multiple concurrent tickets).

## Phase 1: Setup (No Breaking Changes)

### Step 1.1: Create State Manager
✅ **DONE** — Created `scripts/state_manager.py` with:
- `TicketStateManager` class
- Per-ticket read/write operations
- Master index management
- Migration utilities

### Step 1.2: Create Ticket State Directories Structure
```bash
# Run this to initialize the new structure
mkdir -p state/tickets/{1024330,1048701,...}
```

### Step 1.3: Migrate Legacy Singleton Files
```bash
cd /path/to/workspace
python scripts/state_manager.py migrate
```

This reads legacy files:
- `state/pipeline-status.json`
- `state/approval-status.json`

And writes them to:
- `state/tickets/{ticketId}/pipeline-status.json`
- `state/tickets/{ticketId}/approval-status.json`

Creates `state/tickets/index.json` with all ticket metadata.

---

## Phase 2: Update Orchestration Config

### Step 2.1: Add State Resolution to config.json
Update `.github/orchestration/config.json`:

```json
{
  "orchestrator": {
    "agent": "cqlFlowOrchestrator",
    "entryStateFile": "state/run-input.json",
    "stateResolution": {
      "enabled": true,
      "ticketIdSource": "run-input.json",
      "stateFileTemplate": "state/tickets/{ticketId}",
      "pipelineStatusTemplate": "state/tickets/{ticketId}/pipeline-status.json",
      "approvalFileTemplate": "state/tickets/{ticketId}/approval-status.json"
    }
  }
}
```

This tells the orchestrator:
1. Read current ticket ID from `run-input.json`
2. Resolve state file paths using `{ticketId}` template
3. Create ticket directory if missing

---

## Phase 3: Update Agents

Each agent must:
1. **Read** ticket ID from `run-input.json`
2. **Use** `state_manager.py` utilities (or implement equivalent logic)
3. **Write** state to ticket-scoped paths
4. **Update** master index after stage transitions

### Example: Update `ticket-description-intake.agent.md`

**BEFORE:**
```python
import json
pipeline_path = Path("state/pipeline-status.json")
data = json.loads(pipeline_path.read_text())
```

**AFTER:**
```python
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from state_manager import TicketStateManager

ticket_id = TicketStateManager.get_current_ticket_id()
data = TicketStateManager.read_pipeline_status(ticket_id)
```

### Update Pattern
For **all agent files**, apply this pattern:

| Old Code | New Code |
|----------|----------|
| `Path("state/pipeline-status.json").read_text()` | `TicketStateManager.read_pipeline_status(ticket_id)` |
| `Path("state/approval-status.json").read_text()` | `TicketStateManager.read_approval_status(ticket_id)` |
| Write pipeline state | `TicketStateManager.write_pipeline_status(ticket_id, stage, details)` |
| Write approval state | `TicketStateManager.write_approval_status(ticket_id, approved, approved_by, notes)` |

### Agents to Update
1. `ticket-description-intake.agent.md` → calls `TicketStateManager.write_pipeline_status()`
2. `cql-extractor.agent.md` → calls `TicketStateManager.write_pipeline_status()` + `write_approval_status()` (plan prepared, approval pending)
3. `approval-recorder.agent.md` → calls `TicketStateManager.write_approval_status()` + `write_pipeline_status()` (approval recording)
4. `conversion.agent.md` → calls `TicketStateManager.write_pipeline_status()`
5. `pr-submission.agent.md` → calls `TicketStateManager.write_pipeline_status()`

### Agents to Update - Scripts
1. `local-python.enrich_intake` MCP tool → infers ticket id from `state/run-input.json`; replaces `scripts/ado_fallback.py enrich-intake`
2. `local-python.fetch_raw_cql` MCP tool → replaces `scripts/ado_extraction_fallback.py fetch-raw-cql`
3. `local-python.validate_conversion_artifacts` MCP tool → replaces `scripts/validate_conversion_artifacts.py --ticket`

---

## Phase 4: Validation

### Test Scenario: Run Two Tickets Concurrently

**Setup:**
```bash
# Run ticket 1024330
echo '{"ticketId": "1024330"}' > state/run-input.json
# → agent runs, creates state/tickets/1024330/

# Then run ticket 1048701
echo '{"ticketId": "1048701"}' > state/run-input.json
# → agent runs, creates state/tickets/1048701/

# Check index
cat state/tickets/index.json
# Should list both tickets with their stages
```

**Expected Result:**
```json
{
  "currentTicketId": "1048701",
  "lastUpdated": "2026-03-18T15:00:00+05:30",
  "tickets": {
    "1024330": {"stage": "conversion-complete", "approved": true, ...},
    "1048701": {"stage": "intake-complete", "approved": false, ...}
  }
}
```

✅ Both ticket states preserved  
✅ Master index updated  
✅ No state overwrite  

---

## Phase 5: Cleanup (Optional)

### Deprecate Singleton Files
After all agents migrated, you can:

1. **Keep** as legacy fallback (optional):
```bash
# Create symlinks for backward compatibility
ln -s state/tickets/$(cat state/run-input.json | jq -r .ticketId)/pipeline-status.json \
  state/pipeline-status.json
```

2. **Or remove** if all agents migrated:
```bash
rm -f state/pipeline-status.json state/approval-status.json
```

---

## Rollback Plan

If issues arise during migration:

1. **Stop** all running agents
2. **Restore** from git:
   ```bash
   git checkout state/
   ```
3. **Review** phase that failed
4. **Retry** with fixes

---

## Files Modified

| File | Change | Phase |
|------|--------|-------|
| `scripts/state_manager.py` | NEW | 1 |
| `.github/orchestration/config.json` | Add `stateResolution` block | 2 |
| `ticket-description-intake.agent.md` | Use `TicketStateManager` | 3 |
| `cql-extractor.agent.md` | Use `TicketStateManager` | 3 |
| `approval-recorder.agent.md` | Use `TicketStateManager` | 3 |
| `conversion.agent.md` | Use `TicketStateManager` | 3 |
| `pr-submission.agent.md` | Use `TicketStateManager` | 3 |
| `scripts/ado_fallback.py` | Read ticket ID | 3 |

---

## Success Criteria

✅ Multiple tickets can run without state overwrite  
✅ Master index shows all active tickets  
✅ History.json tracks all stage transitions  
✅ Artifacts continue to use `<ticket-id>` naming  
✅ Approval gate still blocks conversion without approval  
✅ All agent handoffs work with per-ticket paths  

