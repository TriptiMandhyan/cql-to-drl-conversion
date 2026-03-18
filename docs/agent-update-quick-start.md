# Quick Start: Update Agents for Per-Ticket State

This guide shows minimal code changes to migrate agents from singleton to per-ticket state management.

## Pattern: Replace Direct File I/O with TicketStateManager

### Before (Singleton - Current)
```python
import json
from pathlib import Path

# Read pipeline status
pipeline_path = Path("state/pipeline-status.json")
pipeline_data = json.loads(pipeline_path.read_text())
ticket_id = pipeline_data.get("ticketId")
stage = pipeline_data.get("stage")

# Read approval status
approval_path = Path("state/approval-status.json")
approval_data = json.loads(approval_path.read_text())
approved = approval_data.get("approved")

# Write new pipeline state
pipeline_data["stage"] = "extraction-complete"
pipeline_path.write_text(json.dumps(pipeline_data, indent=2))
```

### After (Per-Ticket - New)
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from state_manager import TicketStateManager

# Read current ticket ID
ticket_id = TicketStateManager.get_current_ticket_id()

# Read pipeline status
pipeline_data = TicketStateManager.read_pipeline_status(ticket_id)
stage = pipeline_data.get("stage")

# Read approval status
approval_data = TicketStateManager.read_approval_status(ticket_id)
approved = approval_data.get("approved")

# Write new pipeline state (handles index + history automatically)
TicketStateManager.write_pipeline_status(
    ticket_id, 
    "extraction-complete",
    details="Extracted CQL from source files"
)
```

---

## Agent-Specific Updates

### 1. ticket-description-intake.agent.md
**Current behavior:** Writes initial `pipeline-status.json` with stage `intake-complete`

**Change:**
```python
# OLD (lines ~40-50)
pipeline_status = {
    "ticketId": ticket_id,
    "stage": "intake-complete",
    "updatedAt": datetime.now().isoformat(),
    "details": f"..."
}
Path("state/pipeline-status.json").write_text(json.dumps(pipeline_status))

# NEW
from state_manager import TicketStateManager
TicketStateManager.write_pipeline_status(
    ticket_id,
    "intake-complete",
    details=f"..."
)
```

---

### 2. cql-extractor.agent.md
**Current behavior:** Updates `pipeline-status.json` to `extraction-complete`

**Change:**
```python
# OLD
status_data = json.loads(Path("state/pipeline-status.json").read_text())
status_data["stage"] = "extraction-complete"
Path("state/pipeline-status.json").write_text(json.dumps(status_data))

# NEW
from state_manager import TicketStateManager
ticket_id = TicketStateManager.get_current_ticket_id()
TicketStateManager.write_pipeline_status(
    ticket_id,
    "extraction-complete",
    details="Extracted CQL artifacts"
)
```

---

### 3. plan-approval.agent.md
**Current behavior:** Creates plan, sets approval to `false`, updates pipeline to `awaiting-approval`

**Change:**
```python
# OLD
approval_status = {
    "ticketId": ticket_id,
    "approved": False,
    "approvedBy": None,
    "approvedAt": None,
    "notes": ""
}
Path("state/approval-status.json").write_text(json.dumps(approval_status))
pipeline_status["stage"] = "awaiting-approval"
Path("state/pipeline-status.json").write_text(json.dumps(pipeline_status))

# NEW
from state_manager import TicketStateManager
ticket_id = TicketStateManager.get_current_ticket_id()
TicketStateManager.write_approval_status(ticket_id, False, None, "")
TicketStateManager.write_pipeline_status(ticket_id, "awaiting-approval")
```

---

### 4. approval-recorder.agent.md
**Current behavior:** Sets approval to `true` when human approves, updates pipeline to `conversion-ready`

**Change:**
```python
# OLD
approval_status = json.loads(Path("state/approval-status.json").read_text())
approval_status["approved"] = True
approval_status["approvedBy"] = approver_name
approval_status["approvedAt"] = datetime.now().isoformat()
approval_status["notes"] = approval_notes
Path("state/approval-status.json").write_text(json.dumps(approval_status))

pipeline_status = json.loads(Path("state/pipeline-status.json").read_text())
pipeline_status["stage"] = "conversion-ready"
Path("state/pipeline-status.json").write_text(json.dumps(pipeline_status))

# NEW
from state_manager import TicketStateManager
ticket_id = TicketStateManager.get_current_ticket_id()
TicketStateManager.write_approval_status(
    ticket_id, 
    True, 
    approver_name, 
    approval_notes
)
TicketStateManager.write_pipeline_status(ticket_id, "conversion-ready")
```

---

### 5. conversion.agent.md
**Current behavior:** Reads approval state, generates DRL, updates pipeline to `conversion-complete`

**Change:**
```python
# OLD
approval_status = json.loads(Path("state/approval-status.json").read_text())
if not approval_status.get("approved"):
    raise RuntimeError("Conversion blocked: not approved")
    
pipeline_status = json.loads(Path("state/pipeline-status.json").read_text())
pipeline_status["stage"] = "conversion-complete"
Path("state/pipeline-status.json").write_text(json.dumps(pipeline_status))

# NEW
from state_manager import TicketStateManager
ticket_id = TicketStateManager.get_current_ticket_id()
approval_status = TicketStateManager.read_approval_status(ticket_id)
if not approval_status.get("approved"):
    raise RuntimeError("Conversion blocked: not approved")
    
TicketStateManager.write_pipeline_status(ticket_id, "conversion-complete")
```

---

### 6. pr-submission.agent.md
**Current behavior:** Generates PR draft, updates pipeline to `pr-ready` or `pr-submitted`

**Change:**
```python
# OLD
pipeline_status = json.loads(Path("state/pipeline-status.json").read_text())
pipeline_status["stage"] = "pr-submitted"
Path("state/pipeline-status.json").write_text(json.dumps(pipeline_status))

# NEW
from state_manager import TicketStateManager
ticket_id = TicketStateManager.get_current_ticket_id()
TicketStateManager.write_pipeline_status(ticket_id, "pr-submitted")
```

---

## Scripts to Update

### ado_fallback.py (intake helper)
**Current:**
```python
run_input_path = Path("state/run-input.json")
if not run_input_path.exists():
    raise RuntimeError("Ticket id not provided and state/run-input.json not found.")
run_input = json.loads(run_input_path.read_text())
ticket_id = run_input.get("ticketId")
```

**New:**
```python
# Intake helper command:
# python scripts/ado_fallback.py enrich-intake --ticket-id <ticket-id>
# Effect: updates artifacts/intake/<ticket-id>.json cqlPaths in place
```

### ado_extraction_fallback.py (extraction helper)
**New:**
```python
# Extraction helper command:
# python scripts/ado_extraction_fallback.py fetch-raw-cql --ticket-id <ticket-id>
# Effect: writes raw CQL files under artifacts/extraction/raw/<ticket-id>/
# and writes artifacts/extraction/<ticket-id>-fetched.json
```

---

## Testing Each Update

After updating an agent, test with:

```bash
# Setup test ticket
echo '{"ticketId": "9999999"}' > state/run-input.json

# Run agent
# Should create state/tickets/9999999/pipeline-status.json
# Should create state/tickets/index.json

# Verify
ls -la state/tickets/9999999/
cat state/tickets/index.json
```

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: state_manager` | Wrong import path | Check `sys.path.insert(0, ...)` points to scripts dir |
| `FileNotFoundError: No pipeline-status.json` | Agent not creating ticket dir | Ensure `write_pipeline_status()` is called (auto-creates) |
| Index not updating | Using `write_ticket_state()` instead of `write_pipeline_status()` | Use high-level methods like `write_pipeline_status()` which auto-update index |
| History not recorded | Direct path writes bypass history | Use `TicketStateManager` methods, not `Path().write_text()` |

---

## Checklist: Agent Update Complete

- [ ] Imported `TicketStateManager` from `state_manager`
- [ ] Replaced all `Path("state/pipeline-status.json").read_text()` calls
- [ ] Replaced all `Path("state/approval-status.json").read_text()` calls
- [ ] Replaced all direct `.write_text()` calls with `TicketStateManager.write_*()` methods
- [ ] Verified agent gets ticket ID from `run-input.json` (not inferred from legacy files)
- [ ] Tested with a new ticket ID (e.g., 9999999)
- [ ] Verified `state/tickets/{ticketId}/` created correctly
- [ ] Verified `state/tickets/index.json` updated
- [ ] Verified previous tickets' states still exist
