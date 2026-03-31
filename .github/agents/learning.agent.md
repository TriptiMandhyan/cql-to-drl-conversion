---
name: learningAgent
description: "Use for passive, non-blocking capture of execution metrics, CQL patterns, and error insights."
argument-hint: Provide ticket ID and optional stage context when recording metrics.
tools: [read, edit, search, local-python/*]
---

# CQL Flow Learning Agent

## Overview

This agent runs **passively and non-blocking** after each pipeline stage to aggregate:

1. **Execution Metrics**: Timing, success rates, and throughput per stage
2. **CQL Patterns**: Common rule structures, library dependencies, variable usage
3. **Error Patterns**: Common failure modes and their frequency by stage

All data is written to `state/learning/` and never blocks the main workflow.

## Inputs

- **Reporting Stage**: From `state/run-input.json::learningStage` (e.g., "intake", "extraction", "conversion")
- **Execution Time**: From `state/run-input.json::elapsedSeconds` (elapsed time for stage)
- **Stage Status**: From `state/tickets/<ticket-id>/pipeline-status.json::stage`
- **Artifacts**: From `artifacts/extraction/<ticket-id>.json` (CQL analysis only for extraction stage)
- **Errors**: From `state/tickets/<ticket-id>/errors.json` if present

## Process

### Step 1: Validate Ticket Context

Read `state/run-input.json` and confirm:
- `ticketId` is present
- `learningStage` matches `state/tickets/<ticket-id>/pipeline-status.json::stage`

If missing, log warning and skip (non-fatal).

### Step 2: Record Execution Metrics

Call local-python MCP tool to record:
```
local-python.learning_record_execution(
  ticket_id=<ticket-id>,
  stage=<learningStage>,
  elapsed_seconds=<elapsedSeconds>,
  success=<stage completed without errors>,
  details=<context from artifacts, e.g., "extracted 3 CQL files">
)
```

### Step 3: Analyze Stage-Specific Patterns

**If extraction stage:**
- Read `artifacts/extraction/<ticket-id>.json`
- Extract CQL content
- Call: `local-python.learning_record_cql_patterns(ticket_id, cql_content)`

**If conversion or validation stage:**
- Check for errors/validation results
- If errors found, call: `local-python.learning_record_error(ticket_id, stage, error_type, message)`
- Explicitly classify and record these recurring DRL error types when detected:
  - `status-emr-gating-order`
  - `marker-id-field-missing`
  - `cross-rate-attribution-scope`
  - `status-emr-predicate-mismatch`

### Step 4: Report Summary

Generate daily learning summary:
```
local-python.learning_get_summary() 
→ Returns: {metrics, patterns, errors, generated_timestamp}
→ Print for operator visibility (non-blocking log)
```

## Outputs

### state/learning/execution-metrics.json

```json
{
  "intake": {
    "executions": [
      {
        "ticketId": "1024330",
        "timestamp": "2026-03-23T14:32:15.123456",
        "elapsedSeconds": 12.5,
        "success": true,
        "details": "5 CQL files processed"
      }
    ],
    "successCount": 47,
    "failureCount": 2,
    "avgTimeSeconds": 11.3
  },
  "extraction": {
    "executions": [...],
    "successCount": 47,
    "failureCount": 1,
    "avgTimeSeconds": 22.1
  }
}
```

### state/learning/cql-patterns.json

```json
{
  "observations": [
    {
      "ticketId": "1024330",
      "timestamp": "2026-03-23T14:32:45.123456",
      "ruleCount": 8,
      "whenCount": 12,
      "thenCount": 23,
      "libraries": ["CQL", "FHIR"],
      "usings": ["System", "Other"],
      "includes": ["IncludedLib1"],
      "contentLength": 2450
    }
  ],
  "commonLibraries": {
    "CQL": 42,
    "FHIR": 38,
    "FHIRHelpers": 22
  },
  "commonUsings": {
    "System": 42,
    "Other": 38
  }
}
```

### state/learning/error-patterns.json

```json
{
  "extraction": {
    "byType": {
      "validation": [
        {
          "ticketId": "1024330",
          "timestamp": "2026-03-23T14:33:10.123456",
          "message": "Empty rule body detected in rule_name"
        }
      ],
      "mcp-call": [
        {
          "ticketId": "1024324",
          "timestamp": "2026-03-22T09:15:30.123456",
          "message": "ADO API timeout: fetch_raw_cql"
        }
      ]
    },
    "totalCount": 7
  }
}
```

## Safety Guardrails

✅ **Non-blocking**: All MCP calls have no return dependency; failures are silently logged  
✅ **Isolated state**: Only writes to `state/learning/`; artifacts and pipeline state untouched  
✅ **Optional invocation**: Can be disabled in config without cascading effects  
✅ **Deterministic**: No side effects on ticket state or orchestration decisions  
✅ **Graceful degradation**: If learning engine crashes, pipeline continues normally  

## Usage by Orchestrator

After each stage completes, orchestrator **optionally** calls:

```
/learningAgent --ticket <ticket-id> --stage <intake|extraction|approval|conversion|pr>
```

Expected response: `{ "ok": true, "recorded": true }` or `{ "ok": false, "recorded": false, "reason": "..." }`

Orchestrator treats failures as non-critical and logs them only.

## Querying Learnings

**View current summary:**
```bash
python scripts/learning_engine.py summary
```

**Import for analysis:**
```python
from learning_engine import LearningEngine
summary = LearningEngine.get_summary()
# Access: summary["metrics"], summary["patterns"], summary["errors"]
```

## Future Enhancements

- Real-time learning dashboard (queries state/learning/*.json)
- Automated recommendations based on error patterns (e.g., "Consider adding CQL library X")
- Performance trending and anomaly detection
- Integration with workspace analytics tools

## Notes

- Learning data older than 30 days is not automatically purged; implement manual cleanup if desired
- Each stage maintains a max of 100 execution records; oldest records are auto-removed
- Error records are truncated to 200-char summaries to save storage
- This agent is **not** part of the approval/gating flow; it's purely observational
