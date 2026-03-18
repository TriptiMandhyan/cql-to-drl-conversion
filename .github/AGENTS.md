# Agent Registry

This file documents the local custom agents and their responsibilities.

## Adapted Pattern

- Keep VS Code slash agents as the execution surface.
- Add a lightweight orchestration manifest in `.github/orchestration/config.json`.
- Keep reusable stage prompt modules in `.github/agents/prompts/`.
- Enforce slash-only execution from chat; do not require users to run python scripts directly.
- If utilities are used, they are data-fetch helpers only and must not define stage policy or business rules.

## Agents

0. `cql-flow-orchestrator.agent.md`
- Slash command: `/cqlFlowOrchestrator`
- Recommends and enforces next valid slash-agent in sequence based on pipeline state.

1. `ticket-description-intake.agent.md`
- Slash command: `/ticketDescriptionIntakeAgent`
- Reads a single ticket URL placeholder, fetches ticket description, extracts PR links, and resolves PR source branches.
- Writes normalized intake artifact for downstream agents.

2. `cql-extractor.agent.md`
- Slash command: `/cql-extractor`
- Pulls CQL source and extracts structured semantics.
- Writes extraction artifact used by planning.

3. `plan-approval.agent.md`
- Slash command: `/plan-approval`
- Generates implementation plan and checks approval gate.
- Stops execution until approval status is set to approved.

4. `approval-recorder.agent.md`
- Slash command: `/approvalRecorder`
- Records human approval and moves state to `conversion-ready`.

5. `conversion.agent.md`
- Slash command: `/conversion`
- Converts approved CQL semantics to DRL.
- Uses `.github/skills/cql-to-drl/SKILL.md` and guide.

6. `pr-submission.agent.md`
- Slash command: `/pr-submission`
- Builds PR summary, risk notes, and validation checklist.
- Produces final PR draft artifact.

## Coherence Pattern

- Every agent reads prior stage artifact from `artifacts/`.
- Every agent writes exactly one primary stage artifact set for its stage.
- Every agent updates `state/pipeline-status.json` with stage state.
- Conversion must reference `.github/skills/cql-to-drl/cql-to-drl-guide.md` in mapping notes.
- Conversion must follow reference-style fact modeling (platform domain facts + marker/helper declares only).
- Approval transition from `awaiting-approval` to `conversion-ready` is done via `/approvalRecorder`.
