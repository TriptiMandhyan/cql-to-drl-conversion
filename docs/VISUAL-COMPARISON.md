# Visual Comparison: Before vs. After

## File Structure Comparison

### BEFORE: Singleton State Files
```
workspace/
├── state/
│   ├── run-input.json                      # Current ticket URL
│   ├── pipeline-status.json                # SINGLE file (overwrites)
│   └── approval-status.json                # SINGLE file (overwrites)
└── artifacts/
    ├── intake/
    │   ├── 1024330.json                    # ✓ Preserved
    │   └── 1048701.json                    # ✓ Preserved
    ├── extraction/
    │   ├── 1024330.json                    # ✓ Preserved
    │   └── 1048701.json                    # ✓ Preserved
    └── conversion/
        ├── 1024330.drl                     # ✓ Preserved
        └── 1048701.drl                     # ✓ Preserved

PROBLEM: state/pipeline-status.json contains ONLY ticket 1048701
         (ticket 1024330's stage is LOST when 1048701 runs)
```

### AFTER: Per-Ticket State Directories
```
workspace/
├── state/
│   ├── run-input.json                      # Current ticket URL
│   └── tickets/                            # ✨ NEW
│       ├── index.json                      # ✨ Master index (all tickets)
│       ├── 1024330/                        # ✨ Isolated per-ticket state
│       │   ├── pipeline-status.json        # Stage saved
│       │   ├── approval-status.json        # Approval saved
│       │   └── history.json                # Audit trail
│       ├── 1048701/                        # ✨ Isolated per-ticket state
│       │   ├── pipeline-status.json        # Stage saved
│       │   ├── approval-status.json        # Approval saved
│       │   └── history.json                # Audit trail
│       └── 1024415/                        # ✨ NEW ticket (no overwrite)
│           ├── pipeline-status.json        # New stage
│           ├── approval-status.json        # New approval
│           └── history.json                # New history
└── artifacts/
    ├── intake/
    │   ├── 1024330.json                    # ✓ Preserved
    │   ├── 1048701.json                    # ✓ Preserved
    │   └── 1024415.json                    # ✓ NEW
    ├── extraction/
    │   ├── 1024330.json
    │   ├── 1048701.json
    │   └── 1024415.json
    └── conversion/
        ├── 1024330.drl
        ├── 1048701.drl
        └── 1024415.drl

SOLUTION: All three tickets' state is PRESERVED
          state/tickets/index.json shows all three with their stages
```

---

## Data Flow Comparison

### BEFORE: Singleton Overwrite Pattern
```
┌─────────────────────────────────────────────────────────────┐
│                      Ticket 1024330                         │
├─────────────────────────────────────────────────────────────┤
│  Agent → Reads "state/run-input.json"                       │
│       → Processes ticket 1024330                            │
│       → Writes pipeline-status.json {ticketId: 1024330} ✓   │
│                                                             │
│  NOW state/pipeline-status.json = ticket 1024330 data       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                      Ticket 1048701                         │
├─────────────────────────────────────────────────────────────┤
│  User edits "state/run-input.json" → ticket 1048701 URL     │
│  Agent → Processes ticket 1048701                           │
│       → Writes pipeline-status.json {ticketId: 1048701} ✗   │
│                                                             │
│  NOW state/pipeline-status.json = ticket 1048701 data       │
│  LOST: ticket 1024330 state is overwritten!                 │
└─────────────────────────────────────────────────────────────┘
```

### AFTER: Per-Ticket Isolation Pattern
```
┌──────────────────────────────────────────────────────────────┐
│                      Ticket 1024330                          │
├──────────────────────────────────────────────────────────────┤
│  User: echo '{"ticketId": "1024330"}' > run-input.json       │
│  Agent → Reads run-input.json → ticket_id = "1024330"        │
│       → Processes ticket 1024330                             │
│       → Writes state/tickets/1024330/pipeline-status.json ✓  │
│       → Updates state/tickets/index.json ✓                   │
│                                                              │
│  state/tickets/1024330/pipeline-status.json = saved          │
│  state/tickets/index.json:{tickets:{1024330:{...}}}          │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│                      Ticket 1048701                          │
├──────────────────────────────────────────────────────────────┤
│  User: echo '{"ticketId": "1048701"}' > run-input.json       │
│  Agent → Reads run-input.json → ticket_id = "1048701"        │
│       → Processes ticket 1048701                             │
│       → Writes state/tickets/1048701/pipeline-status.json ✓  │
│       → Updates state/tickets/index.json ✓                   │
│                                                              │
│  state/tickets/1048701/pipeline-status.json = saved          │
│  state/tickets/index.json:{tickets:{1024330:{...},           │
│                                      1048701:{...}}}         │
│  PRESERVED: ticket 1024330 state STILL EXISTS! ✓             │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│                      Ticket 1024415 (Later)                  │
├──────────────────────────────────────────────────────────────┤
│  User: echo '{"ticketId": "1024415"}' > run-input.json       │
│  Agent → Processes ticket 1024415                            │
│       → Writes state/tickets/1024415/pipeline-status.json ✓  │
│       → Updates state/tickets/index.json ✓                   │
│                                                              │
│  state/tickets/index.json shows ALL THREE:                   │
│  {tickets:{1024330:{stage:...}, 1048701:{stage:...},         │
│            1024415:{stage:...}}}                             │
│  NOTHING LOST! ✓✓✓                                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Master Index: What It Tracks

### BEFORE: No Index
```
✗ No way to quickly list all active tickets
✗ No way to know which stage each ticket is in (unless you read artifacts)
✗ Current ticket state is in run-input.json, but history is lost
```

### AFTER: Master Index
```json
{
  "currentTicketId": "1024415",
  "lastUpdated": "2026-03-18T15:00:00+05:30",
  "tickets": {
    "1024330": {
      "stage": "conversion-complete",
      "approved": true,
      "ingestedAt": "2026-03-18T10:00:00+05:30"
    },
    "1048701": {
      "stage": "awaiting-approval", 
      "approved": false,
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

✓ Quick lookup: Which stage is ticket 1048701 in? → awaiting-approval  
✓ Approval status: Is ticket 1048701 approved? → false  
✓ Timestamps: When was each ticket ingested?  
✓ Dashboard ready: Can build UI showing all tickets + their stages  

---

## Per-Ticket History: Audit Trail

### BEFORE: No History
```
✗ No way to know when ticket 1024330 transitioned from
  "intake-complete" → "extraction-complete" → "awaiting-approval"
✗ No way to track who/what made the state transitions
✗ Lost if logs are purged
```

### AFTER: Complete History
```json
{
  "ticketId": "1024330",
  "transitions": [
    {
      "stage": "intake-complete",
      "timestamp": "2026-03-18T10:05:00+05:30",
      "actor": "ticketDescriptionIntakeAgent"
    },
    {
      "stage": "extraction-complete",
      "timestamp": "2026-03-18T10:15:00+05:30",
      "actor": "cql-extractor"
    },
    {
      "stage": "awaiting-approval",
      "timestamp": "2026-03-18T10:20:00+05:30",
      "actor": "plan-approval"
    },
    {
      "stage": "conversion-ready",
      "timestamp": "2026-03-18T14:14:00+05:30",
      "actor": "approvalRecorder"
    },
    {
      "stage": "conversion-complete",
      "timestamp": "2026-03-18T14:30:00+05:30",
      "actor": "conversion"
    }
  ]
}
```

✓ Audit trail: When did each stage transition happen?  
✓ Traceability: Which agent made the transition?  
✓ Debugging: How did ticket 1024330 get to current state?  
✓ Compliance: Permanent record for audits  

---

## Code Update Pattern

### BEFORE: Direct File I/O (Error-Prone)
```python
# OLD CODE
import json
from pathlib import Path

# Read state
data = json.loads(Path("state/pipeline-status.json").read_text())
ticket_id = data.get("ticketId")

# Modify state
data["stage"] = "extraction-complete"

# Write state (overwrites, no index update, no history)
Path("state/pipeline-status.json").write_text(json.dumps(data))
```

❌ Manual path management  
❌ Easy to forget index update  
❌ Easy to forget history entry  
❌ No atomic writes (crash = corruption)  
❌ No per-ticket isolation  

### AFTER: Abstracted via Manager (Clean)
```python
# NEW CODE
from state_manager import TicketStateManager

# Get current ticket
ticket_id = TicketStateManager.get_current_ticket_id()

# Update state (one method call)
TicketStateManager.write_pipeline_status(
    ticket_id,
    "extraction-complete",
    details="Extracted CQL from source files"
)
```

✓ Single method call  
✓ Auto-creates ticket directory  
✓ Auto-updates index ✓  
✓ Auto-adds history  
✓ Atomic writes  
✓ Per-ticket isolation  

---

## Configuration: Before vs. After

### BEFORE: Static Paths
```json
{
  "orchestrator": {
    "entryStateFile": "state/pipeline-status.json",
    "approvalFile": "state/approval-status.json"
  }
}
```

❌ Always reads same files → singleton  
❌ Cannot support multiple tickets  

### AFTER: Templated + Resolved at Runtime
```json
{
  "orchestrator": {
    "entryStateFile": "state/run-input.json",
    "stateResolution": {
      "enabled": true,
      "ticketIdSource": "run-input.json",
      "pipelineStatusTemplate": "state/tickets/{ticketId}/pipeline-status.json",
      "approvalFileTemplate": "state/tickets/{ticketId}/approval-status.json"
    }
  }
}
```

✓ Entry point tells system which ticket to work on  
✓ Placeholders resolved at runtime  
✓ Supports unlimited concurrent tickets  
✓ Agent developers don't need to know config details  

---

## Example: Running 3 Tickets

### BEFORE: State Lost on Each New Ticket
```bash
# Ticket 1024330 runs
$ /plan-approval
  → Creates artifacts/plan/1024330.md
  → state/pipeline-status.json = {ticketId: 1024330, stage: awaiting-approval}
  → Master index? (doesn't exist)

# Switch to ticket 1048701
$ echo '{"ticketId": "1048701"}' > state/run-input.json

# Ticket 1048701 runs  
$ /cql-extractor
  → Creates artifacts/extraction/1048701.json
  → state/pipeline-status.json = {ticketId: 1048701, stage: extraction-complete}
  → ❌ LOST: What stage is ticket 1024330 in? (unknown)

# Switch to ticket 1024415
$ echo '{"ticketId": "1024415"}' > state/run-input.json

# Ticket 1024415 runs
$ /ticketDescriptionIntakeAgent
  → Creates artifacts/intake/1024415.json
  → state/pipeline-status.json = {ticketId: 1024415, stage: intake-complete}
  → ❌ LOST: What happened to tickets 1024330 and 1048701?
```

### AFTER: All State Preserved
```bash
# Ticket 1024330 runs
$ /plan-approval
  → state/tickets/1024330/pipeline-status.json = {stage: awaiting-approval}
  → state/tickets/index.json = {tickets: {1024330: {stage: awaiting-approval}}}

# Switch to ticket 1048701
$ echo '{"ticketId": "1048701"}' > state/run-input.json

# Ticket 1048701 runs
$ /cql-extractor
  → state/tickets/1048701/pipeline-status.json = {stage: extraction-complete}
  → state/tickets/index.json = {tickets: {
       1024330: {stage: awaiting-approval},    ← PRESERVED
       1048701: {stage: extraction-complete}
     }}
  → ✓ Both tickets tracked

# Switch to ticket 1024415
$ echo '{"ticketId": "1024415"}' > state/run-input.json

# Ticket 1024415 runs
$ /ticketDescriptionIntakeAgent
  → state/tickets/1024415/pipeline-status.json = {stage: intake-complete}
  → state/tickets/index.json = {tickets: {
       1024330: {stage: awaiting-approval},    ← PRESERVED
       1048701: {stage: extraction-complete},  ← PRESERVED
       1024415: {stage: intake-complete}
     }}
  → ✓ All three tickets tracked, nothing lost!

# Check status of all tickets
$ cat state/tickets/index.json
# {
#   "tickets": {
#     "1024330": {"stage": "awaiting-approval", ...},
#     "1048701": {"stage": "extraction-complete", ...},
#     "1024415": {"stage": "intake-complete", ...}
#   }
# }
```

---

## Summary Table

| Aspect | Before | After |
|--------|--------|-------|
| **State Files** | Singleton (1) | Per-ticket (N) |
| **Max Concurrent Tickets** | 1 | Unlimited |
| **State on New Ticket** | Overwritten ❌ | Isolated ✓ |
| **Master Index** | None | Yes ✓ |
| **History Tracking** | No | Per-ticket ✓ |
| **Audit Trail** | Lost ❌ | Permanent ✓ |
| **Query "What stage?"** | Guess from artifacts ❌ | Query index ✓ |
| **Code Complexity** | Scattered ❌ | Abstracted ✓ |
| **Data Loss Risk** | High ❌ | None ✓ |
| **Migration Path** | N/A | Backward compat ✓ |

