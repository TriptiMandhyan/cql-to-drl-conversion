# Workspace Instructions: CQL to DRL Agents

## Mission

Build and operate a local multi-agent workflow that transforms CQL artifacts into DRL deliverables with strict approval and traceability gates.

## Core Rules

1. Never proceed to PR submission without explicit approval state set to approved.
2. Preserve ticket id, source CQL file paths, and commit references in every output artifact.
3. Do not fabricate unknown business logic. Mark assumptions explicitly.
4. Keep all generated artifacts in project folders (`artifacts/`, `state/`, `templates/` outputs).
5. Never store secrets in files. Use environment variables only.
6. Use MCP tools only for ADO metadata/content/state operations; do not use direct REST URL/PAT calls from agent workflows.
7. Intake cannot complete unless `artifacts/intake/<ticket-id>.json` has non-empty `cqlPaths`; extraction cannot complete unless raw CQL content is fetched for required paths and extraction/plan artifacts are written.
8. Never assume approval from prior runs or existing state; PR submission requires an explicit approval command in the current run with an approver name provided at approval time.
9. PR packaging must include supplemental measure JSON (from authenticated API response) and measure Java test file required by rules-engine runtime.

## Agent Handoff Contract

Each phase must produce machine-readable handoff outputs:

- Intake: `artifacts/intake/<ticket-id>.json`
- Extraction: `artifacts/extraction/<ticket-id>.json`
- Plan: `artifacts/plan/<ticket-id>.md` and `state/tickets/<ticket-id>/approval-status.json`
- Conversion: `artifacts/conversion/<measure-slug>.drl` (one per changed CQL) and `artifacts/conversion/<ticket-id>-mapping.md`
- API Artifact: `artifacts/pr-assets/<ticket-id>/<measure-slug>.json`
- Test Artifact: `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java`
- PR: `artifacts/pr/<ticket-id>-pr.md`

## Definition of Done

A ticket is done only if:

- Plan is approved by human reviewer.
- DRL compiles against local validation checks (or known blockers are documented).
- Mapping from CQL clauses to DRL rules is documented.
- Measure JSON file is generated from authenticated API response and prepared for PR.
- Measure Java test file is generated in canonical year/measure/rate naming pattern and prepared for PR.
- PR draft content is generated with validation summary.
