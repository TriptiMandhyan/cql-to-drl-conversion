# Agent File Map

This file explains why each major markdown file exists and how the major files connect.

## Flow Diagram

```mermaid
flowchart TD
    CI[copilot-instructions.md]
    AG[AGENTS.md]
    CFG[orchestration/config.json]
    ORCH[agents/cql-flow-orchestrator.agent.md]
    PROTO[agents/prompts/agent_protocol.md]

    INTAKE[agents/ticket-description-intake.agent.md]
    INTAKEP[agents/prompts/intake.md]
    EXTRACT[agents/cql-extractor.agent.md]
    EXTRACTP[agents/prompts/extraction.md]
    APPROVAL[agents/approval-recorder.agent.md]
    RESET[agents/ticket-status-reset.agent.md]
    CONVERT[agents/conversion.agent.md]
    SEMANTIC[agents/semantic-check.agent.md]
    APIART[agents/api-artifact-builder.agent.md]
    TESTART[agents/test-run-file-builder.agent.md]
    PR[agents/pr-submission.agent.md]

    SKILL[skills/cql-to-drl/SKILL.md]
    GUIDE[skills/cql-to-drl/cql-to-drl-guide.md]

    CI --> ORCH
    CI --> INTAKE
    CI --> EXTRACT
    CI --> APPROVAL
    CI --> RESET
    CI --> CONVERT
    CI --> SEMANTIC
    CI --> APIART
    CI --> TESTART
    CI --> PR

    CFG --> ORCH
    CFG --> INTAKE
    CFG --> EXTRACT
    CFG --> APPROVAL
    CFG --> RESET
    CFG --> CONVERT
    CFG --> SEMANTIC
    CFG --> APIART
    CFG --> TESTART
    CFG --> PR

    ORCH --> PROTO
    ORCH --> INTAKE
    ORCH --> EXTRACT
    ORCH --> APPROVAL
    ORCH --> RESET
    ORCH --> CONVERT
    ORCH --> SEMANTIC
    ORCH --> APIART
    ORCH --> TESTART
    ORCH --> PR

    CFG --> INTAKEP
    CFG --> EXTRACTP

    INTAKEP --> INTAKE
    EXTRACTP --> EXTRACT

    SKILL --> GUIDE
    SKILL --> CONVERT
    GUIDE --> CONVERT
    GUIDE --> SEMANTIC

    AG -.documents.-> CFG
    AG -.documents.-> ORCH
    AG -.documents.-> INTAKE
    AG -.documents.-> EXTRACT
    AG -.documents.-> APPROVAL
    AG -.documents.-> RESET
    AG -.documents.-> CONVERT
    AG -.documents.-> SEMANTIC
    AG -.documents.-> APIART
    AG -.documents.-> TESTART
    AG -.documents.-> PR
    AG -.documents.-> SKILL
    AG -.documents.-> GUIDE
```

## Why Each Markdown File Exists

| File | Why it exists | Needs config.json |
|---|---|---|
| `.github/copilot-instructions.md` | Workspace-wide operating rules for all agent work. | No |
| `.github/AGENTS.md` | Human-readable map of the file graph so the workflow is understandable and maintainable. | No |
| `.github/agents/cql-flow-orchestrator.agent.md` | Defines the stage order and decides which stage should run next. | Yes |
| `.github/agents/prompts/agent_protocol.md` | Shared contract for how agents read state, write artifacts, and respect guardrails. | Indirectly |
| `.github/agents/ticket-description-intake.agent.md` | Defines how intake turns a ticket into a normalized intake artifact. | Yes |
| `.github/agents/prompts/intake.md` | Minimal intake prompt content referenced by the manifest for the intake stage. | Yes |
| `.github/agents/cql-extractor.agent.md` | Defines how intake output becomes structured extraction output and initial plan/approval-pending artifacts. | Yes |
| `.github/agents/prompts/extraction.md` | Minimal extraction prompt content referenced by the manifest for the extraction stage. | Yes |
| `.github/agents/approval-recorder.agent.md` | Defines how explicit human approval details are recorded before PR submission. | Yes |
| `.github/agents/ticket-status-reset.agent.md` | Defines how a ticket's pipeline and approval status are reset for a clean rerun. | Yes |
| `.github/agents/conversion.agent.md` | Defines how extraction output becomes DRL and mapping output. | Yes |
| `.github/agents/semantic-check.agent.md` | Defines how post-conversion semantic drift review is recorded before downstream artifact generation. | Yes |
| `.github/agents/api-artifact-builder.agent.md` | Defines how local-python MCP retrieves authenticated API payloads and converts them into PR-ready measure JSON. | Yes |
| `.github/agents/test-run-file-builder.agent.md` | Defines how the PR-ready Java test run file is generated from a canonical template. | Yes |
| `.github/agents/pr-submission.agent.md` | Defines how converted output becomes a PR draft and GitHub update. | Yes |
| `.github/skills/cql-to-drl/SKILL.md` | Conversion rulebook used to keep DRL generation consistent and enforce non-negotiable constraints. | No |
| `.github/skills/cql-to-drl/cql-to-drl-guide.md` | Detailed conversion reference used by the conversion stage and mapping output. | No |

## What config.json Is For

`.github/orchestration/config.json` is the runtime manifest.

It exists because the workflow needs one place to define:

- stage order
- which agent file belongs to each stage
- optional prompt modules for stages that use them
- which files each stage writes
- global guardrails
- GitHub repository settings used by PR submission

Without `config.json`, the orchestrator and the stage agents would not have a shared source of truth for sequencing and guardrails.

## Files That Directly Need config.json

These files read or depend on `.github/orchestration/config.json` at runtime:

- `.github/agents/cql-flow-orchestrator.agent.md`
- `.github/agents/ticket-description-intake.agent.md`
- `.github/agents/cql-extractor.agent.md`
- `.github/agents/approval-recorder.agent.md`
- `.github/agents/ticket-status-reset.agent.md`
- `.github/agents/conversion.agent.md`
- `.github/agents/semantic-check.agent.md`
- `.github/agents/api-artifact-builder.agent.md`
- `.github/agents/test-run-file-builder.agent.md`
- `.github/agents/pr-submission.agent.md`
- prompt modules referenced inside `config.json`

## Config References That Matter

`config.json` currently points to these prompt modules:

- `.github/agents/prompts/intake.md`
- `.github/agents/prompts/extraction.md`

Additional shared protocol file:

- `.github/agents/prompts/agent_protocol.md`

## Minimal Dependency Rules

- All stage agents depend on `copilot-instructions.md` for workspace rules.
- All runtime stages depend on `config.json` for sequencing and guardrails.
- The orchestrator depends on `agent_protocol.md` for shared behavior.
- The conversion stage depends on both `SKILL.md` and `cql-to-drl-guide.md`.
- Intake and extraction are the only stages currently using prompt modules from config.

## Runtime Guide

Detailed run flow, exact commands, MCP startup location, and stage-by-stage verification are in:

- `docs/runtime-flow.md`
