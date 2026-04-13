# Runtime Flow Guide

This guide covers the complete workflow for transforming CQL artifacts into DRL rules. Follow the setup instructions first, then execute the stages in order using slash commands.

## End-to-End Workflow Diagram

```mermaid
flowchart TD
    START([Start Run])
    ENV[Set env vars: ADO_PAT, GITHUB_TOKEN]
    INPUT[state/run-input.json]
    CFG[.github/orchestration/config.json]
    MCP[.vscode/mcp.json loaded by VS Code]

    ORCHCMD[/cqlFlowOrchestrator]
    ORCHFILE[.github/agents/cql-flow-orchestrator.agent.md]

    INTAKECMD[/ticketDescriptionIntakeAgent]
    INTAKEFILE[.github/agents/ticket-description-intake.agent.md]
    INTAKEOUT[artifacts/intake/<ticket-id>.json]
    PIPE[state/tickets/<ticket-id>/pipeline-status.json]

    FALLBACK{intake cqlPaths empty\nand fallback allowed?}
    FALLBACKCMD[MCP tool: local-python.enrich_intake\n(ticket_id=<ticket-id>)]

    EXTRACTCMD[/cql-extractor]
    EXTRACTFILE[.github/agents/cql-extractor.agent.md]
    EXTRACTOUT[artifacts/extraction/<ticket-id>.json]

    PLANOUT[artifacts/plan/<ticket-id>.md]
    APPROVALSTATE[state/tickets/<ticket-id>/approval-status.json]

    APPROVECMD[/approvalRecorder]
    APPROVEFILE[.github/agents/approval-recorder.agent.md]

    CONVERTCMD[/conversion]
    CONVERTFILE[.github/agents/conversion.agent.md]
    SKILL[.github/skills/cql-to-drl/SKILL.md]
    GUIDE[.github/skills/cql-to-drl/cql-to-drl-guide.md]
    CONVERTOUT[artifacts/conversion/<measure-slug>.drl\nartifacts/conversion/<ticket-id>-mapping.md]
    VALIDATECMD[MCP tool: local-python.validate_conversion_artifacts\n(ticket_id=<ticket-id>)]
    SEMANTICCMD[/semanticCheck]
    SEMANTICFILE[.github/agents/semantic-check.agent.md]
    SEMANTICOUT[artifacts/review/<ticket-id>-semantic-check.md]

    APICMD[/apiArtifactBuilder]
    APIFILE[.github/agents/api-artifact-builder.agent.md]
    APIOUT[artifacts/pr-assets/<ticket-id>/<measure-slug>.json]

    TESTCMD[/testRunFileBuilder]
    TESTFILE[.github/agents/test-run-file-builder.agent.md]
    TESTOUT[artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java]

    PRCMD[/pr-submission]
    PRFILE[.github/agents/pr-submission.agent.md]
    PROUT[artifacts/pr/<ticket-id>-pr.md]

    START --> ENV --> INPUT --> MCP --> ORCHCMD
    ORCHCMD --> ORCHFILE
    ORCHFILE --> CFG

    ORCHCMD --> INTAKECMD --> INTAKEFILE --> INTAKEOUT --> PIPE
    INTAKEOUT --> FALLBACK
    FALLBACK -- yes --> FALLBACKCMD --> INTAKEOUT
    FALLBACK -- no --> EXTRACTCMD

    INTAKEOUT --> EXTRACTCMD --> EXTRACTFILE --> EXTRACTOUT --> PLANOUT --> APPROVALSTATE --> PIPE
    PIPE --> CONVERTCMD --> CONVERTFILE
    CONVERTFILE --> SKILL
    CONVERTFILE --> GUIDE
    CONVERTCMD --> CONVERTOUT --> VALIDATECMD --> PIPE
    PIPE --> SEMANTICCMD --> SEMANTICFILE --> SEMANTICOUT --> PIPE
    PIPE --> APICMD --> APIFILE --> APIOUT --> PIPE
    PIPE --> TESTCMD --> TESTFILE --> TESTOUT --> APPROVALSTATE --> PIPE
    PIPE --> APPROVECMD --> APPROVEFILE --> APPROVALSTATE --> PIPE
    PIPE --> PRCMD --> PRFILE --> PROUT --> PIPE
```

## Setup Prerequisites

Before running any workflow, complete the following one-time setup.

### 1. Install Dependencies

Install the local MCP server requirements:

```powershell
python -m pip install -r config/mcp/requirements-local-mcp.txt
```

### 2. Set Environment Variables

Set your authentication tokens in your PowerShell session:

```powershell
$env:ADO_PAT = "<your-ado-personal-access-token>"
$env:GITHUB_TOKEN = "<your-github-personal-access-token>"
$env:API_AUTH_BASIC_TOKEN = "<your-basic-auth-token-for-auth-api>"
```

To persist these across sessions, use:

```powershell
setx ADO_PAT "<your-ado-personal-access-token>"
setx GITHUB_TOKEN "<your-github-personal-access-token>"
setx API_AUTH_BASIC_TOKEN "<your-basic-auth-token-for-auth-api>"
```

### 3. Start the Local MCP Server

Open a separate PowerShell terminal and run:

```powershell
python scripts/local_mcp_server.py
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8765
```

**This server must be running before you execute any workflow stage.** The server provides local-python MCP tools for state management, CQL processing, and validation.

If you modify `scripts/local_mcp_server.py` or `scripts/state_manager.py`, restart this process to load your changes.

### 4. Prepare Your Input

Create `state/run-input.json` with your ticket ID:

```json
{
  "ticketId": "1024330"
}
```

Alternatively, use a full ticket URL:

```json
{
  "ticketUrl": "https://dev.azure.com/healthcatalyst/MeasureAble%202.0/_workitems/edit/1024330/"
}
```

## Workflow Configuration

The workflow is configured by:

- **Manifest**: `.github/orchestration/config.json` (defines agents, states, guardrails)
- **MCP Setup**: `.vscode/mcp.json` (VS Code loads MCP servers from here)
- **Orchestrator Agent**: `.github/agents/cql-flow-orchestrator.agent.md` (coordinates all stages)

## Running the Workflow

### Start the Orchestrator

In VS Code Copilot Chat, run:

```
/cqlFlowOrchestrator
```

The orchestrator will:
1. Read your ticket ID from `state/run-input.json`
2. Check the current pipeline status
3. Recommend the next agent to run

### Execute Stages in Order

Run each of these commands in sequence:

1. **`/ticketDescriptionIntakeAgent`** – Extracts PR links and CQL file paths from the ticket
2. **`/cql-extractor`** – Analyzes CQL and generates extraction artifacts + plan
3. **`/conversion`** – Converts CQL to DRL rules using the plan
4. **`/semanticCheck`** – Reviews DRL/mapping outputs for semantic drift and writes a review report
5. **`/apiArtifactBuilder`** – Retrieves auth token and writes canonical measure JSON artifact
6. **`/testRunFileBuilder`** – Generates canonical Java test-run file
7. **`/approvalRecorder`** – Records human approval (only step that requires user input)
8. **`/pr-submission`** – Generates PR draft and opens a pull request

**Do not skip stages.** Each stage depends on outputs from previous stages.

## Verification: What to Check After Each Stage

| Stage | Expected Outputs | Location |
|-------|-----------------|----------|
| **Intake** | Resolved PR links and CQL paths | `artifacts/intake/<ticket-id>.json` |
| **Extraction** | Parsed CQL rules, generation plan | `artifacts/extraction/<ticket-id>.json` <br/> `artifacts/plan/<ticket-id>.md` |
| **Conversion** | Generated DRL files and mapping | `artifacts/conversion/<ticket-id>-mapping.md` <br/> `artifacts/conversion/*.drl` |
| **Semantic Check** | Semantic drift review report | `artifacts/review/<ticket-id>-semantic-check.md` |
| **API Artifact** | Authenticated payload captured as measure JSON | `artifacts/pr-assets/<ticket-id>/<measure-slug>.json` |
| **Test Artifact** | Canonical Java test file generated | `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java` |
| **Approval** | Approval decision recorded and PR unlock stage set | `state/tickets/<ticket-id>/approval-status.json` <br/> (`approved: true`) |
| **PR Submission** | Draft PR with validation summary | `artifacts/pr/<ticket-id>-pr.md` |

After each stage completes successfully, check the output files to confirm the next stage's inputs are correct.

## State Management

The workflow maintains per-ticket state in `state/tickets/<ticket-id>/`:

- **`pipeline-status.json`** – Current stage and progress
- **`approval-status.json`** – Approval decision and timestamp
- **`history.json`** – Timeline of stage transitions
- **`index.json`** – Master index tracking all tickets (shared)

You can view the current status:

```powershell
cat state/tickets/<ticket-id>/pipeline-status.json
```

## Resetting a Ticket

If you need to restart a ticket from the beginning:

```
/ticketStatusReset
```

This command will:
- Reset pipeline stage to `intake-start`
- Clear approval status
- Preserve all artifacts (for manual review if needed)

## MCP Tools Reference

These tools are available during workflow execution:

| Tool | Purpose | Example Use |
|------|---------|-------------|
| `local-python.enrich_intake` | Fetch PR changes if initial intake is empty | Called automatically if needed |
| `local-python.fetch_raw_cql` | Download CQL files from commit | Called during extraction |
| `local-python.validate_conversion_artifacts` | Validate generated DRL | Called after conversion |
| `local-python.state_read_pipeline` | Read current pipeline status | For reporting/debugging |
| `local-python.state_read_approval` | Read approval status | For reporting/debugging |
| `local-python.state_write_pipeline` | Update pipeline stage | Used by agents automatically |
| `local-python.state_write_approval` | Record approval decision | Used by approval agent |
| `local-python.learning_record_execution` | Log stage timing and success (optional) | Background metrics only |

All state operations use MCP tools—**do not edit state files directly**.

## Troubleshooting

### "MCP tool not found" Error

**Cause**: Local MCP server is not running.  
**Fix**: Start the server in a separate terminal: `python scripts/local_mcp_server.py`

### "ticket-id not found in state files"

**Cause**: `state/run-input.json` is missing or doesn't contain `ticketId`.  
**Fix**: Create/update `state/run-input.json` with a valid ticket ID.

### "PR submission blocked: not approved"

**Cause**: Approval status is `false`; you skipped or didn't complete `/approvalRecorder`.  
**Fix**: Run `/approvalRecorder` and provide approver details to unlock PR submission.

### "CQL did not download again"

**Cause**: CQL fetching is performed by `/cql-extractor` only. If you resume from `conversion-ready` or later, extraction is skipped and no new fetch occurs.  
**Fix**: Re-run extraction for the ticket. If you want a clean re-run, execute `/ticketStatusReset`, then run `/ticketDescriptionIntakeAgent` followed by `/cql-extractor`.

### "Extractor ran but I still see old CQL content"

**Cause**: Fetch is commit-pinned to intake PR metadata (`sourceCommitId`). If intake is stale, extraction re-fetches the same commit snapshot.  
**Fix**: Re-run intake first to refresh PR metadata, then run extractor again.

### "Empty DRL file generated"

**Cause**: CQL extraction found no valid rules or conversion has placeholder-only logic.  
**Fix**: Check `artifacts/extraction/<ticket-id>.json` for parsed rules. If empty, review the source CQL for syntax errors.

### "PR creation failed"

**Cause**: GitHub token is invalid or the target branch already exists.  
**Fix**: Verify `GITHUB_TOKEN` is set correctly. Check if you need to reset the ticket and try again.

### Changes Not Reflecting After Code Update

**Cause**: You edited `scripts/local_mcp_server.py` or `scripts/state_manager.py` but didn't restart the server.  
**Fix**: Stop the local MCP server (Ctrl+C) and restart it to load your changes.

## Key Files

| File | Purpose |
|------|---------|
| `.github/orchestration/config.json` | Manifest defining agents, states, and guardrails |
| `.github/agents/cql-flow-orchestrator.agent.md` | Main orchestrator agent |
| `.github/agents/*.agent.md` | Individual stage agents (intake, extraction, etc.) |
| `.github/skills/cql-to-drl/SKILL.md` | CQL-to-DRL conversion skill |
| `.github/skills/cql-to-drl/cql-to-drl-guide.md` | Reference guide for CQL-to-DRL mappings |
| `scripts/local_mcp_server.py` | Local MCP server implementation |
| `scripts/state_manager.py` | Per-ticket state management |
| `scripts/learning_engine.py` | Background metrics aggregation |
| `.vscode/mcp.json` | MCP server configuration for VS Code |

## Directory Structure

```
devopsToPRAgents/
├── .github/
│   ├── orchestration/          # Workflow configuration
│   ├── agents/                 # Stage agents and orchestrator
│   └── skills/cql-to-drl/      # Conversion skill and guide
├── scripts/                    # Helper scripts and MCP server
├── artifacts/                  # Generated outputs by stage
│   ├── intake/
│   ├── extraction/
│   ├── conversion/
│   └── pr/
├── state/                      # Per-ticket and learning state
│   ├── tickets/                # Per-ticket state directories
│   │   └── <ticket-id>/
│   │       ├── pipeline-status.json
│   │       ├── approval-status.json
│   │       ├── history.json
│   │       └── index.json
│   └── learning/               # Aggregated metrics and patterns
│       ├── execution-metrics.json
│       ├── cql-patterns.json
│       └── error-patterns.json
└── config/mcp/                 # MCP dependencies and configuration
```

## Advanced: Parallel Ticket Processing

The workflow supports processing multiple tickets concurrently. Each ticket maintains its own state in `state/tickets/<ticket-id>/`:

1. Create multiple `run-input.json` snapshots or use a job queue
2. Each orchestrator invocation reads its own `state/run-input.json`
3. Per-ticket state directories prevent conflicts
4. You can run `/cqlFlowOrchestrator` for different tickets in parallel windows

Ticket state is isolated; one ticket's failure does not affect others.
