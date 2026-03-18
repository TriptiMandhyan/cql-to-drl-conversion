# Runtime Flow Guide

This file is the operational runbook for this project.

## End-to-End Run Diagram

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
    PIPE[state/pipeline-status.json]

    FALLBACK{intake cqlPaths empty\nand fallback allowed?}
    FALLBACKCMD[python scripts/ado_fallback.py\nenrich-intake --ticket-id <ticket-id>]

    EXTRACTCMD[/cql-extractor]
    EXTRACTFILE[.github/agents/cql-extractor.agent.md]
    EXTRACTOUT[artifacts/extraction/<ticket-id>.json]

    PLANCMD[/plan-approval]
    PLANFILE[.github/agents/plan-approval.agent.md]
    PLANOUT[artifacts/plan/<ticket-id>.md]
    APPROVALSTATE[state/approval-status.json]

    APPROVECMD[/approvalRecorder]
    APPROVEFILE[.github/agents/approval-recorder.agent.md]

    CONVERTCMD[/conversion]
    CONVERTFILE[.github/agents/conversion.agent.md]
    SKILL[.github/skills/cql-to-drl/SKILL.md]
    GUIDE[.github/skills/cql-to-drl/cql-to-drl-guide.md]
    CONVERTOUT[artifacts/conversion/<cql-basename>.drl\nartifacts/conversion/<ticket-id>-mapping.md]
    VALIDATECMD[python scripts/validate_conversion_artifacts.py\n--ticket <ticket-id>]

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

    INTAKEOUT --> EXTRACTCMD --> EXTRACTFILE --> EXTRACTOUT --> PIPE
    EXTRACTOUT --> PLANCMD --> PLANFILE --> PLANOUT --> APPROVALSTATE --> PIPE
    PIPE --> APPROVECMD --> APPROVEFILE --> APPROVALSTATE --> PIPE

    APPROVALSTATE --> CONVERTCMD --> CONVERTFILE
    CONVERTFILE --> SKILL
    CONVERTFILE --> GUIDE
    CONVERTCMD --> CONVERTOUT --> VALIDATECMD --> PIPE

    PIPE --> PRCMD --> PRFILE --> PROUT --> PIPE
```

## Working Directory

Run from workspace root:

- `devopsToPRAgents/`

## MCP Startup Source

MCP server config location:

- `.vscode/mcp.json`

How MCP starts:

- VS Code starts MCP servers for this workspace from `.vscode/mcp.json`.
- Do not run MCP servers manually in a normal run.
- If MCP tools are missing, reload the VS Code window while this workspace is open.

Defined MCP servers:

- `ado` (auth from `ADO_PAT`)
- `github` (auth from `GITHUB_TOKEN`)

## Required Environment Variables

PowerShell current session:

```powershell
$env:ADO_PAT = "<your-ado-pat>"
$env:GITHUB_TOKEN = "<your-github-token>"
```

Windows persistent:

```powershell
setx ADO_PAT "<your-ado-pat>"
setx GITHUB_TOKEN "<your-github-token>"
```

## Required Input File

Set one ticket in:

- `state/run-input.json`

Example:

```json
{
  "ticketUrl": "https://dev.azure.com/healthcatalyst/MeasureAble%202.0/_workitems/edit/<ticket-id>/"
}
```

## Exact Stage Commands (Copilot Chat)

Run in this order:

```text
/ticketDescriptionIntakeAgent
/cql-extractor
/plan-approval
/approvalRecorder
/conversion
/pr-submission
```

## Python Commands Used In Flow

Run only when needed:

```powershell
python scripts/ado_fallback.py enrich-intake --ticket-id <ticket-id>
python scripts/validate_conversion_artifacts.py --ticket <ticket-id>
```

Command purpose:

- `ado_fallback.py enrich-intake`: intake-only helper to enrich intake `cqlPaths` when MCP coverage is not enough.
- `validate_conversion_artifacts.py`: validates conversion outputs after `/conversion`.

## Stage Output Checks

- After `/ticketDescriptionIntakeAgent`: `artifacts/intake/<ticket-id>.json`
- After `/cql-extractor`: `artifacts/extraction/<ticket-id>.json`
- After `/plan-approval`: `artifacts/plan/<ticket-id>.md` and `state/approval-status.json` with `approved: false`
- After `/approvalRecorder`: `state/approval-status.json` with `approved: true`
- After `/conversion`: `artifacts/conversion/<ticket-id>-mapping.md` and DRL file(s)
- After `/pr-submission`: `artifacts/pr/<ticket-id>-pr.md`

## Files Required For Successful Run

- `.github/orchestration/config.json`
- `.vscode/mcp.json`
- `.github/agents/*.agent.md`
- `.github/skills/cql-to-drl/SKILL.md`
- `.github/skills/cql-to-drl/cql-to-drl-guide.md`
- `state/run-input.json`
