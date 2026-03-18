# Multi-Ticket State Management Architecture

## Problem
Current architecture overwrites state files when a new ticket runs:
- `state/run-input.json` → single ticket URL
- `state/pipeline-status.json` → single ticket stage
- `state/approval-status.json` → single ticket approval

**Impact:** Running ticket 1024415 overwrites state from ticket 1048701, losing traceability.

## Proposed Solution

### New State Directory Structure
```
state/
├── run-input.json                    # Current entry point (unchanged)
├── tickets/
│   ├── index.json                    # Master index of all tickets + current run
│   ├── 1024330/
│   │   ├── pipeline-status.json      # Per-ticket pipeline stage
│   │   ├── approval-status.json      # Per-ticket approval state
│   │   └── history.json              # Timestamp log of all stage changes
│   ├── 1048701/
│   │   ├── pipeline-status.json
│   │   ├── approval-status.json
│   │   └── history.json
│   └── 1024415/
│       ├── pipeline-status.json
│       ├── approval-status.json
│       └── history.json
```

### File Schemas

#### `state/tickets/index.json` (Master Index)
```json
{
  "currentTicketId": "1024415",
  "lastUpdated": "2026-03-18T14:15:00+05:30",
  "tickets": {
    "1024330": {
      "stage": "conversion-complete",
      "approved": true,
      "ingestedAt": "2026-03-18T10:00:00+05:30"
    },
    "1048701": {
      "stage": "conversion-complete",
      "approved": true,
      "ingestedAt": "2026-03-18T12:00:00+05:30"
    },
    "1024415": {
      "stage": "intake-complete",
      "approved": false,
      "ingestedAt": "2026-03-18T14:15:00+05:30"
    }
  }
}
```

#### `state/tickets/{ticketId}/pipeline-status.json` (Per-Ticket)
```json
{
  "ticketId": "1024415",
  "stage": "intake-complete",
  "updatedAt": "2026-03-18T14:15:00+05:30",
  "details": "..."
}
```

#### `state/tickets/{ticketId}/approval-status.json` (Per-Ticket)
```json
{
  "ticketId": "1024415",
  "approved": false,
  "approvedBy": null,
  "approvedAt": null,
  "notes": ""
}
```

#### `state/tickets/{ticketId}/history.json` (Audit Trail)
```json
{
  "ticketId": "1024415",
  "transitions": [
    {
      "stage": "intake-complete",
      "timestamp": "2026-03-18T14:15:00+05:30",
      "actor": "ticketDescriptionIntakeAgent"
    }
  ]
}
```

### Migration Path

#### Step 1: Update Orchestration Config
[Update `.github/orchestration/config.json`]
- Change `approvalFile` → `state/tickets/{ticketId}/approval-status.json`
- Change `entryStateFile` → `state/tickets/{ticketId}/pipeline-status.json`
- Add rule to resolve `{ticketId}` from `run-input.json` at runtime

#### Step 2: Create Ticket-Scoped Utilities
Create `scripts/state_manager.py`:
- `get_ticket_state_path(ticket_id, filename)` → resolves per-ticket path
- `read_ticket_state(ticket_id, filename)` → reads per-ticket state with fallback
- `write_ticket_state(ticket_id, filename, data)` → atomic writes per-ticket state
- `add_to_index(ticket_id, stage, approved)` → updates master index
- `get_current_ticket_id()` → reads from `run-input.json`

#### Step 3: Update All Agents
For each agent, replace:
```python
# OLD
state_path = "state/pipeline-status.json"
approval_path = "state/approval-status.json"

# NEW
ticket_id = get_current_ticket_id()  # from run-input.json
state_path = get_ticket_state_path(ticket_id, "pipeline-status.json")
approval_path = get_ticket_state_path(ticket_id, "approval-status.json")
```

#### Step 4: Update Agent Handoff Specs
Agents must:
1. Read ticket ID from `run-input.json`
2. Create ticket subdirectory if missing: `mkdir state/tickets/{ticketId}`
3. Read/write state from ticket-scoped paths
4. Update master index after each stage transition

### Backwards Compatibility
- Keep `state/run-input.json` as single-ticket entry point (user still edits this)
- Maintain legacy singleton files as **deprecated symlinks** for 1 release (optional)
- All new agents use per-ticket paths only

### Key Benefits
✅ **Multi-ticket concurrency**: Run ticket 1024415 without losing 1048701 state  
✅ **Full audit trail**: `history.json` tracks every stage transition  
✅ **Master index**: Quick lookup of all in-flight tickets and their stages  
✅ **Backward compatible**: Existing agents can work during transition  
✅ **No artifact changes**: Artifacts stay in `artifacts/{phase}/{ticket-id}.*`  

### Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| Agent configs become complex with path templating | Create state_manager utility to hide complexity |
| Agents not updated → read/write wrong paths | Update orchestration validation to reject old-style paths |
| Legacy tickets have no history.json | Generate history.json during migration script for existing tickets |

