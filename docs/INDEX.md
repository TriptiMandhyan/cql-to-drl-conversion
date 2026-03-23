# Multi-Ticket State Management: Complete Solution Index

**Created:** March 18, 2026  
**Status:** ✅ Design Complete & Implemented  
**Problem:** Ticket state overwritten when new tickets run  
**Solution:** Per-ticket state directories with master index  

---

## 📋 Quick Links (Start Here)

1. **Executive Summary** → [SOLUTION-SUMMARY.md](SOLUTION-SUMMARY.md)
   - 5-minute overview of problem, solution, timeline, risks

2. **Visual Comparison** → [VISUAL-COMPARISON.md](VISUAL-COMPARISON.md)
   - Before/after diagrams, data flow, code examples

3. **For Architects** → [state-architecture-proposal.md](state-architecture-proposal.md)
   - Directory structure, schemas, benefits, risks

4. **For Developers** → [agent-update-quick-start.md](agent-update-quick-start.md)
   - Code patterns, per-agent updates, testing procedures

5. **For DevOps** → [migration-to-per-ticket-state.md](migration-to-per-ticket-state.md)
   - Phased implementation, validation scenarios, rollback plan

---

## 📦 Deliverables

### Core Implementation
- **[scripts/state_manager.py](../../scripts/state_manager.py)** (146 lines)
  - Utility class `TicketStateManager`
  - Per-ticket state read/write operations
  - Master index management
  - Backward-compatibility migration
  - Usage: `from state_manager import TicketStateManager`

### Configuration
- **[.github/orchestration/config-v2.0-per-ticket.json](../../.github/orchestration/config-v2.0-per-ticket.json)** (150 lines)
  - `stateResolution` block for runtime ticket ID resolution
  - Per-agent `stateManager` references
  - Template patches for `{ticketId}` placeholder
  - Ready to merge into `config.json`

### Documentation

#### For Decision Makers
- **[SOLUTION-SUMMARY.md](SOLUTION-SUMMARY.md)** (150 lines)
  - Executive summary with timeline, costs, benefits
  - Risk matrix with mitigations
  - Success metrics and next steps

#### For Architects
- **[state-architecture-proposal.md](state-architecture-proposal.md)** (120 lines)
  - Directory structure with rationale
  - JSON schemas for all state files
  - Migration path description
  - Benefits vs. risks analysis

#### For Developers
- **[agent-update-quick-start.md](agent-update-quick-start.md)** (180 lines)
  - Before/after code samples for each agent
  - Per-agent update procedures (6 agents)
  - Per-script updates (3 scripts)
  - Testing checklist and troubleshooting

#### For DevOps/Implementation
- **[migration-to-per-ticket-state.md](migration-to-per-ticket-state.md)** (200 lines)
  - 5-phase implementation guide
  - Pre-migration setup (no breaking changes)
  - Agent update sequencing
  - Validation test scenario
  - Rollback procedures
  - Success criteria checklist

#### For Visualization
- **[VISUAL-COMPARISON.md](VISUAL-COMPARISON.md)** (200 lines)
  - Before/after directory structures
  - Data flow diagrams
  - Master index composition
  - History tracking examples
  - Live ticket execution example
  - Summary comparison table

---

## 🎯 What Problem Does This Solve?

### Before
```
Run ticket 1024330 → state/pipeline-status.json = 1024330's state
Run ticket 1048701 → state/pipeline-status.json = 1048701's state
                    ❌ LOST: 1024330's state overwritten
```

### After
```
Run ticket 1024330 → state/tickets/1024330/pipeline-status.json ✓
Run ticket 1048701 → state/tickets/1048701/pipeline-status.json ✓
                    ✓ Both states coexist
                    ✓ Master index shows both
```

---

## 📊 Implementation Overview

### Files to Create
✅ `scripts/state_manager.py` - Utility class  
✅ `.github/orchestration/config-v2.0-per-ticket.json` - New config template  
✅ All documentation files above  

### Files to Update
- `ticket-description-intake.agent.md` - Use `TicketStateManager`
- `cql-extractor.agent.md` - Use `TicketStateManager`
- `approval-recorder.agent.md` - Use `TicketStateManager` (approval recording only)
- `conversion.agent.md` - Use `TicketStateManager`
- `pr-submission.agent.md` - Use `TicketStateManager`
- Use MCP tool `local-python.enrich_intake` for intake-stage `cqlPaths` enrichment (replaces `ado_fallback.py`)
- Use MCP tool `local-python.fetch_raw_cql` for extraction-stage commit-pinned raw CQL retrieval (replaces `ado_extraction_fallback.py`)
- Use MCP tool `local-python.validate_conversion_artifacts` for conversion artifact validation (replaces direct `validate_conversion_artifacts.py` call)

### New Directory Structure
```
state/
├── run-input.json                    # Keep (entry point)
└── tickets/                          # NEW
    ├── index.json                    # NEW (master index)
    ├── {ticketId}/
    │   ├── pipeline-status.json      # NEW (per-ticket)
    │   ├── approval-status.json      # NEW (per-ticket)
    │   └── history.json              # NEW (audit trail)
```

---

## ⏱️ Implementation Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| 1. Setup | 30 min | Initialize, migrate, create dirs |
| 2. Config | 1 hour | Update orchestration config |
| 3. Agents | 6-8 hours | Update 6 agent files |
| 4. Scripts | 2-3 hours | Update 3 script files |
| 5. Testing | 2 hours | Validation and integration tests |
| **Total** | **12-15 hours** | Parallelizable across team |

---

## ✅ Success Criteria

- [ ] Multiple tickets run without state overwrite
- [ ] Master index (`state/tickets/index.json`) shows all tickets
- [ ] Each ticket has isolated state in `state/tickets/{id}/`
- [ ] History.json tracks all stage transitions
- [ ] Approval gate still enforces approval before conversion
- [ ] Artifacts continue using `<ticket-id>` naming
- [ ] No breaking changes to existing deployments
- [ ] All integration tests pass

---

## 🚀 Quick Start (Copy-Paste Commands)

```bash
# 1. Initialize ticket directories
mkdir -p state/tickets

# 2. Migrate existing singleton files (if any exist)
cd /path/to/workspace
python scripts/state_manager.py migrate

# 3. Verify migration
ls -la state/tickets/
cat state/tickets/index.json

# 4. Test with a new ticket
echo '{"ticketId": "9999999"}' > state/run-input.json
# Then run any agent
# Verify: ls state/tickets/9999999/
```

---

## 👥 Document Audience

| Role | Start With | Then Read |
|------|------------|-----------|
| **Manager/Lead** | SOLUTION-SUMMARY.md | VISUAL-COMPARISON.md |
| **Architect** | state-architecture-proposal.md | migration-to-per-ticket-state.md |
| **Developer** | agent-update-quick-start.md | Individual agent specs |
| **DevOps/SRE** | migration-to-per-ticket-state.md | SOLUTION-SUMMARY.md |
| **Reviewer** | VISUAL-COMPARISON.md | state-architecture-proposal.md |

---

## 🔄 Migration Strategy

### Option 1: Gradual (Recommended)
- Week 1: Setup + config update
- Week 2: Agent 1-3 updates
- Week 3: Agent 4-6 + script updates
- Week 4: Integration testing + stabilization

### Option 2: Aggressive
- Execute all 5 phases in 1-2 days
- Requires full team focus
- Higher risk of issues

### Option 3: Dual Support (Safest)
- Use symlinks from legacy → new paths
- Old agents work via symlinks
- Migrate agents gradually
- Full cutover after 2-3 weeks

---

## 🧪 Validation Test Scenario

Run these commands to verify the solution works:

```bash
# Setup
mkdir -p state/tickets
python scripts/state_manager.py migrate

# Test 1: Run ticket 1024330
echo '{"ticketId": "1024330"}' > state/run-input.json
# Run agents for 1024330
# Verify: state/tickets/1024330/ created with state files

# Test 2: Run ticket 1048701
echo '{"ticketId": "1048701"}' > state/run-input.json  
# Run agents for 1048701
# Verify: state/tickets/1048701/ created AND 1024330/ unchanged

# Test 3: Check master index
cat state/tickets/index.json
# Should show BOTH tickets with their stages

# Test 4: Verify history
cat state/tickets/1024330/history.json
cat state/tickets/1048701/history.json
# Should show all transitions with timestamps
```

---

## ⚠️ Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Developers forget new methods | Medium | Code review + tests |
| Config templating breaks | Medium | Dry-run validation |
| Ticket ID parsing fails | Low | Input validation |
| Index corruption | Low | Atomic writes + backup |
| Concurrent writes | Low | Documentation |

See [SOLUTION-SUMMARY.md](SOLUTION-SUMMARY.md#risk-mitigation) for full details.

---

## 📞 Questions?

### Architecture Questions
→ Read [state-architecture-proposal.md](state-architecture-proposal.md)

### "How do I update my agent?"
→ Read [agent-update-quick-start.md](agent-update-quick-start.md)

### "What's the full timeline?"
→ Read [migration-to-per-ticket-state.md](migration-to-per-ticket-state.md#timeline-estimate)

### "What if something breaks?"
→ Read [migration-to-per-ticket-state.md](migration-to-per-ticket-state.md#rollback-plan)

### "Why should we do this?"
→ Read [VISUAL-COMPARISON.md](VISUAL-COMPARISON.md)

---

## 📝 Files in This Solution

| File | Lines | Purpose |
|------|-------|---------|
| scripts/state_manager.py | 146 | Core utility |
| state-architecture-proposal.md | 120 | Design rationale |
| migration-to-per-ticket-state.md | 200 | Implementation guide |
| agent-update-quick-start.md | 180 | Developer reference |
| .github/orchestration/config-v2.0-per-ticket.json | 150 | Config template |
| SOLUTION-SUMMARY.md | 150 | Executive summary |
| VISUAL-COMPARISON.md | 200 | Diagrams & examples |
| **TOTAL** | **~1,100 lines** | Complete solution |

---

## 🎓 Key Learning: TicketStateManager API

All agents and scripts use these methods:

```python
from state_manager import TicketStateManager

# Read
ticket_id = TicketStateManager.get_current_ticket_id()
pipeline = TicketStateManager.read_pipeline_status(ticket_id)
approval = TicketStateManager.read_approval_status(ticket_id)

# Write
TicketStateManager.write_pipeline_status(ticket_id, "stage", "details")
TicketStateManager.write_approval_status(ticket_id, approved, approved_by, notes)

# Query
all_tickets = TicketStateManager.get_all_tickets()

# Admin
TicketStateManager.migrate_singleton_files()
```

That's it! Developers don't need to know about directory structures or index updates.

---

## 🏁 Next Steps

1. **Review** with team (send SOLUTION-SUMMARY.md + VISUAL-COMPARISON.md)
2. **Approve** architecture (PR/sign-off)
3. **Schedule** migration window
4. **Execute** phases 1-5 in order
5. **Monitor** first week
6. **Document** lessons learned

---

**Status:** Ready to implement  
**Maintenance:** Minimal (state manager handles complexity)  
**Support:** All documentation and code provided  

