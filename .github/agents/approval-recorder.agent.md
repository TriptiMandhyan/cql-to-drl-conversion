---
name: approvalRecorder
description: "Use when plan stage is complete and human approval must be recorded before conversion."
tools: [read, edit]
---

# Approval Recorder Agent

## Purpose

Record explicit human approval and unlock conversion only when the pipeline is at the approval gate.

## Inputs

- `state/pipeline-status.json`
- `state/approval-status.json`
- approver name (prompt user if not provided)
- optional approval note

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.approvalRequiredBeforeConversion` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

0. Read `.github/orchestration/config.json` and enforce approval guardrails.
1. Read `state/pipeline-status.json` and confirm stage is `awaiting-approval`.
2. Read current `state/approval-status.json`.
3. Write updated approval state:
   - `ticketId`: from pipeline
   - `approved`: true
   - `approvedBy`: provided approver
   - `approvedAt`: current ISO timestamp
   - `notes`: provided note or default
4. Update `state/pipeline-status.json` to `conversion-ready`.

## Outputs

- Updated `state/approval-status.json`
- Updated `state/pipeline-status.json`

## Guardrails

- Never set approval true unless pipeline stage is `awaiting-approval`.
- Never change `ticketId` to a different value than current pipeline state.
- Do not proceed to conversion in this stage; only set `conversion-ready`.
