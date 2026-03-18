---
name: plan-approval
description: "Use when extraction is complete and an implementation plan must be drafted and paused for human approval."
tools: [read, edit, search]
---

# Plan and Approval Agent

## Purpose

Generate the conversion plan and enforce the human approval gate.

## Inputs

- `artifacts/extraction/<ticket-id>.json`
- `templates/plan-template.md`

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.approvalRequiredBeforeConversion` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

0. Read `.github/orchestration/config.json` and enforce approval guardrails.
1. Build plan sections using extraction data.
2. Highlight unknowns and risks.
3. Write plan to artifacts folder.
4. Initialize or update approval state with `approved: false`.
5. Stop and wait for human approval update.
6. Update `state/pipeline-status.json` stage to `awaiting-approval` and recommend `/approvalRecorder` as next slash command.

## Outputs

- `artifacts/plan/<ticket-id>.md`
- `state/approval-status.json`

## Guardrails

- Never proceed to conversion in the same run.
- Approval must include approver identity and timestamp.
- Clearly mark assumptions and blockers.
