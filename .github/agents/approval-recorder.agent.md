---
name: approvalRecorder
description: "Use when plan is ready and explicit human approval details must be recorded before conversion."
argument-hint: Provide approver name and optional approval note for the active ticket.
tools: [read, edit, search, local-python/*]
---

# Approval Recorder Agent

## Purpose

Record explicit human approval and unlock conversion after extractor has produced plan and pending approval state.

This stage is the only valid path to mark approval true for the current run.

## Inputs

- `state/run-input.json`
- `state/tickets/<ticket-id>/pipeline-status.json`
- `state/tickets/<ticket-id>/approval-status.json`
- `artifacts/extraction/<ticket-id>.json`
- `artifacts/plan/<ticket-id>.md`
- approver name (prompt user if not provided)
- optional approval note

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.approvalRequiredBeforeConversion` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

0. Read `.github/orchestration/config.json` and `.github/orchestration/statuses.json`; enforce approval guardrails and canonical status values.
1. Resolve `ticketId` from `state/run-input.json` and read `state/tickets/<ticket-id>/pipeline-status.json`; confirm stage is `awaiting-approval`.
2. Read `state/tickets/<ticket-id>/approval-status.json` and verify `approved` is currently `false`.
3. Confirm both `artifacts/extraction/<ticket-id>.json` and `artifacts/plan/<ticket-id>.md` exist for approval context.
4. Require explicit approver identity from the current `/approvalRecorder` command; never infer or reuse approver identity from prior runs, prior ticket state, chat history, or placeholder defaults.
5. Write updated approval state via MCP tool `local-python.state_write_approval(approved=true, approved_by=..., notes=...)`:
   - `ticketId`: from pipeline
   - `approved`: true
   - `approvedBy`: provided approver
   - `approvedAt`: current ISO timestamp
   - `notes`: provided note or default
6. Update pipeline stage via MCP tool `local-python.state_write_pipeline(stage="conversion-ready", details=...)`.

## Outputs

- Updated `state/tickets/<ticket-id>/approval-status.json`
- Updated `state/tickets/<ticket-id>/pipeline-status.json`

## Guardrails

- Never set approval true unless pipeline stage is `awaiting-approval` and approver identity is present.
- Never treat existing `approved=true` from prior ticket history as approval for the current run; require explicit command-time approval details.
- If approver name is missing, stop and request approver identity instead of progressing.
- Never change `ticketId` to a different value than current pipeline state.
- Never generate or modify the plan in this stage.
- Pipeline/approval state writes must use MCP state tools (`local-python.state_write_pipeline`, `local-python.state_write_approval`), not direct file edits.
- Do not proceed to conversion in this stage; only set `conversion-ready`.
