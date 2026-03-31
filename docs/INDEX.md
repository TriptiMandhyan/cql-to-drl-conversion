# Documentation Index

This index lists the active workflow documentation for the current CQL to DRL pipeline.

## Core Docs

1. [architecture.md](architecture.md) - System architecture and stage responsibilities.
2. [runtime-flow.md](runtime-flow.md) - End-to-end execution order, gates, and troubleshooting.
3. [local-runbook.md](local-runbook.md) - Local setup, MCP discipline, and operator run steps.

## Workflow Rules

1. [../.github/copilot-instructions.md](../.github/copilot-instructions.md) - Workspace guardrails and definition of done.
2. [../.github/orchestration/config.json](../.github/orchestration/config.json) - Runtime manifest, guardrails, and agent wiring.
3. [../.github/orchestration/statuses.json](../.github/orchestration/statuses.json) - Canonical pipeline stage values.
4. [../.github/agents/prompts/agent_protocol.md](../.github/agents/prompts/agent_protocol.md) - Shared stage protocol and completion gates.

## Current Stage Order

1. `/ticketDescriptionIntakeAgent`
2. `/cql-extractor`
3. `/conversion`
4. `/apiArtifactBuilder`
5. `/testRunFileBuilder`
6. `/approvalRecorder`
7. `/pr-submission`

Approval is required immediately before PR submission.
