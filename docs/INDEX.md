# Documentation Index

This index reflects the current, active workflow layout and runtime behavior.

## Core docs

1. [docs/architecture.md](architecture.md) - Project architecture and component boundaries.
2. [docs/runtime-flow.md](runtime-flow.md) - End-to-end agent runtime flow and stage transitions.
3. [docs/local-runbook.md](local-runbook.md) - Local execution and troubleshooting playbook.
4. [docs/SOLUTION-SUMMARY.md](SOLUTION-SUMMARY.md) - Current migration and stability summary.

## Runtime source of truth

1. [.github/orchestration/config.json](../.github/orchestration/config.json) - Active orchestrator manifest.
2. [.github/orchestration/statuses.json](../.github/orchestration/statuses.json) - Canonical pipeline stages.
3. [.github/copilot-instructions.md](../.github/copilot-instructions.md) - Workspace-wide Copilot operating rules.

## Agent and skill entry points

1. [.github/agents/README.md](../.github/agents/README.md) - Copilot custom agent map.
2. [.github/AGENTS.md](../.github/AGENTS.md) - File relationship map and rationale.
3. [.github/skills/cql-to-drl/SKILL.md](../.github/skills/cql-to-drl/SKILL.md) - Conversion guardrails and conventions.

## State and artifacts

1. [state/tickets](../state/tickets) - Per-ticket pipeline and approval state.
2. [state/tickets/index.json](../state/tickets/index.json) - Master ticket stage index.
3. [artifacts](../artifacts) - Intake, extraction, plan, conversion, and PR outputs.

## Notes

1. The active config is [.github/orchestration/config.json](../.github/orchestration/config.json).
2. Deprecated template configs are intentionally removed to avoid divergence.
3. DRL generation outputs remain under [artifacts/conversion](../artifacts/conversion).

