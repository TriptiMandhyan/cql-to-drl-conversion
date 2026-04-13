---
name: cqlFlowOrchestrator
description: "Use when you want VS Code slash-agent orchestration for end-to-end CQL to DRL flow with explicit approval gate and agent handoffs."
argument-hint: Provide ticket ID or ticket URL context in state/run-input.json and optionally the stage to resume.
handoffs:
  - label: Intake Ticket
    agent: ticketDescriptionIntakeAgent
    prompt: Pull ticket details, resolve PR references, and write intake artifact.
  - label: Extract CQL
    agent: cql-extractor
    prompt: Build extraction and plan outputs from intake artifact.
  - label: Convert to DRL
    agent: conversion
    prompt: Generate DRL and clause-to-rule mapping from extraction output.
  - label: Run Semantic Check
    agent: semanticCheck
    prompt: Review generated DRL against extraction and mapping artifacts, then write semantic check findings.
  - label: Build API JSON
    agent: apiArtifactBuilder
    prompt: Retrieve auth token, call data API, and write measure JSON artifact.
  - label: Build Test File
    agent: testRunFileBuilder
    prompt: Generate measure Java test file from configured test template.
  - label: Record Approval
    agent: approvalRecorder
    prompt: Record explicit approver details to unlock PR submission.
  - label: Prepare PR
    agent: pr-submission
    prompt: Draft PR content, include supplemental artifacts, and update pipeline stage to pr-submitted.
tools: [read, edit, search, agent]
agents: [ticketDescriptionIntakeAgent, cql-extractor, approvalRecorder, conversion, semanticCheck, apiArtifactBuilder, testRunFileBuilder, pr-submission, ticketStatusReset, learningAgent]
---

# CQL Flow Orchestrator Agent

## Purpose

Coordinate the end-to-end flow using slash-callable agents and state artifacts.

## Pre-Workflow Setup

Before running any agent for the first time on a ticket:

1. Ensure `state/tickets/` directory exists: `mkdir -p state/tickets`
2. Ensure `state/run-input.json` exists with `ticketId` (preferred) or `ticketUrl`
3. The first agent run (intake) will create `state/tickets/<ticketId>/` and initialize both `pipeline-status.json` and `approval-status.json`

## Runtime Context

- Manifest: `.github/orchestration/config.json`
- Shared protocol: `.github/agents/prompts/agent_protocol.md`

## Agent Sequence

1. `/ticketDescriptionIntakeAgent`
2. `/cql-extractor`
3. `/conversion`
4. `/semanticCheck` (optional when `governance.guardrails.semanticCheckRequiredBeforeApiArtifact` is `false`)
5. `/apiArtifactBuilder`
6. `/testRunFileBuilder`
7. pause and request one explicit approval command: `/approvalRecorder` (single call with approver details)
8. `/pr-submission`

## Utility Command

- `/ticketStatusReset` to reset a ticket state to `intake-start` and `approved=false` before rerunning flow.

## Execution Mode

- Execute stages end-to-end in one orchestrator run.
- Do not stop between intake, extraction, conversion, API artifact, test artifact, and PR stages when prerequisites are satisfied.
- Stop exactly once before PR submission, after test artifact stage, and request only the `/approvalRecorder` command with approver details.
- After approval is recorded and pipeline stage is `pr-ready`, continue PR submission automatically.
- If any stage fails guardrails or required artifacts are missing, report blocker and stop.

## Orchestration Rules

- Resolve `ticketId` from `state/run-input.json`, then read `state/tickets/<ticket-id>/pipeline-status.json` and recommend only the next valid agent.
- Enforce slash-only execution guidance; do not ask user to run python or shell scripts.
- Do not use GitHub MCP tools in orchestrator stages before `/pr-submission`; GitHub operations are owned by the PR agent only.
- Enforce MCP-only transport for ADO metadata/content operations; do not recommend direct REST URL/PAT fallback.
- If intake artifact has empty `cqlPaths`, require intake stage to call MCP tool `local-python.enrich_intake` and block extractor until `cqlPaths` is non-empty.
- Require extraction stage to call MCP tool `local-python.fetch_raw_cql` for commit-pinned content and block extraction completion when required CQL content is missing.
- Block PR submission unless approval is true.
- Do not infer approval from prior runs, prior approver names, or pre-existing `approval-status.json` values; require explicit `/approvalRecorder` invocation for the current run.
- Require all state transitions to be written through MCP tools (`local-python.state_write_pipeline`, `local-python.state_write_approval`).
- Require conversion agent to reference `cql-to-drl-guide.md` sections in mapping output.
- Ensure each stage writes its required artifact before moving to next stage.
- Before `/conversion`, verify both `artifacts/extraction/<ticket-id>.json` and `artifacts/plan/<ticket-id>.md` exist for the current ticket.
- Before `/semanticCheck`, verify `artifacts/conversion/<ticket-id>-mapping.md` exists and at least one ticket-relevant DRL file was produced.
- Before `/apiArtifactBuilder`, if `governance.guardrails.semanticCheckRequiredBeforeApiArtifact` is `true`, verify semantic check report exists and pipeline stage is `semantic-check-complete`.
- Before `/apiArtifactBuilder`, if `governance.guardrails.semanticCheckRequiredBeforeApiArtifact` is `false`, allow stage `conversion-complete` and treat semantic report as optional context.
- Before `/testRunFileBuilder`, verify `artifacts/pr-assets/<ticket-id>/<measure-slug>.json` exists.
- Before `/approvalRecorder`, verify `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java` exists.
- Before `/approvalRecorder`, if semantic check gate is enabled, verify `artifacts/review/<ticket-id>-semantic-check.md` exists for reviewer context.
- Before `/pr-submission`, verify `artifacts/conversion/<ticket-id>-mapping.md` exists and at least one ticket-relevant DRL file was produced.
- Before `/pr-submission`, verify `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java` exists.
- Before `/pr-submission`, require conversion details/mapping to explicitly confirm all of the following checks passed:
  - GAP logic is status-derived and not gated by EMR evidence markers.
  - Group/provider marker declarations include id fields used by constraints and inserts populate those ids.
  - Cross-rate group/provider exclusions are attribution-scoped or explicitly documented as approved patient-global behavior.
  - Status and EMR evidence predicates are parity-checked for timing/modifier semantics whenever used for gating.
- Validate governance flags in `.github/orchestration/config.json` before recommending stage transitions.
- **Optional Learning Invocation** (Non-Blocking): After each major stage completes (intake, extraction, conversion, pr), optionally invoke `/learningAgent` for passive metrics aggregation. This is background-only and does not block the main workflow. If learning succeeds (returns ok=true), provide silent progress note; if it fails, suppress failure and continue pipeline.
- Never request human intervention except the single approval command.
- When paused for approval, provide one exact command format including approver name and wait.

## Outputs

- Stage progress updates in chat
- A single approval pause message with exact `/approvalRecorder` command format
- Final completion summary after PR stage
