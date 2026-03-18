# Workspace Instructions: CQL to DRL Agents

## Mission

Build and operate a local multi-agent workflow that transforms CQL artifacts into DRL deliverables with strict approval and traceability gates.

## Core Rules

1. Never proceed from planning to conversion without explicit approval state set to approved.
2. Preserve ticket id, source CQL file paths, and commit references in every output artifact.
3. Do not fabricate unknown business logic. Mark assumptions explicitly.
4. Keep all generated artifacts in project folders (`artifacts/`, `state/`, `templates/` outputs).
5. Never store secrets in files. Use environment variables only.

## Agent Handoff Contract

Each phase must produce machine-readable handoff outputs:

- Intake: `artifacts/intake/<ticket-id>.json`
- Extraction: `artifacts/extraction/<ticket-id>.json`
- Plan: `artifacts/plan/<ticket-id>.md` and `state/approval-status.json`
- Conversion: `artifacts/conversion/<cql-basename>.drl` (one per changed CQL) and `artifacts/conversion/<ticket-id>-mapping.md`
- PR: `artifacts/pr/<ticket-id>-pr.md`

## Definition of Done

A ticket is done only if:

- Plan is approved by human reviewer.
- DRL compiles against local validation checks (or known blockers are documented).
- Mapping from CQL clauses to DRL rules is documented.
- PR draft content is generated with validation summary.
