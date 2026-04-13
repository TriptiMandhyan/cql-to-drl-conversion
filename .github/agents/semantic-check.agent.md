---
name: semanticCheck
description: "Use when conversion artifacts are complete and a semantic drift review must be recorded before downstream PR assets are generated."
argument-hint: Provide ticket ID context and ensure conversion outputs already exist for the current ticket.
tools: [read, edit, search, local-python/*]
---

# Semantic Check Agent

## Purpose

Review generated DRL and mapping artifacts against extracted CQL intent, and write a semantic check report that captures drift risks before API/test/approval stages continue.

## Inputs

- `state/run-input.json`
- `state/tickets/<ticket-id>/pipeline-status.json`
- `artifacts/extraction/<ticket-id>.json`
- `artifacts/plan/<ticket-id>.md`
- `artifacts/conversion/<measure-slug>.drl`
- `artifacts/conversion/<ticket-id>-mapping.md`
- `.github/skills/cql-to-drl/SKILL.md`
- `.github/skills/cql-to-drl/cql-to-drl-guide.md`
- `templates/semantic-check-template.md`

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.
- `governance.guardrails.guideReferenceRequiredInMapping` must be enforced.

## Review Focus

Check for semantic drift, especially around:

1. Missing or partially mapped extraction clauses.
2. Comparator/operator changes (`>`, `>=`, `<`, `<=`, `=`).
3. OR/AND regrouping drift.
4. Null/empty predicate tightening.
5. Earliest versus latest evidence-selection drift.
6. Encounter-subject versus patient-subject output mismatch.
7. `option_id = all` clauses not expanded to concrete option rows.
8. Collapsed option families or naming consolidation that changes measure behavior.
9. Unresolved shared-library or domain TODOs still present in mapping notes.
10. Any intentional deviation from source CQL or reference DRL that lacks an explicit rationale.

## Steps

1. Read `.github/orchestration/config.json` and `.github/orchestration/statuses.json`; confirm current stage is `conversion-complete`.
2. Resolve `ticketId` from `state/run-input.json`.
3. Read extraction, plan, DRL, and mapping artifacts for the current ticket.
4. Compare extraction clauses and mapping rows to ensure every materially relevant clause has DRL coverage.
5. Review the generated DRL for the semantic-preservation risks listed above, using `.github/skills/cql-to-drl/SKILL.md` and `.github/skills/cql-to-drl/cql-to-drl-guide.md` as the review rubric.
6. Write `artifacts/review/<ticket-id>-semantic-check.md` using `templates/semantic-check-template.md`.
7. Set report outcome to one of:
   - `PASS`: no material semantic drift found.
   - `WARN`: review-worthy semantic risk remains, but downstream artifact generation may continue if the report documents the risk clearly.
   - `FAIL`: semantic drift or unresolved blockers are too significant to advance.
8. If outcome is `FAIL`, stop and do not advance pipeline stage.
9. If outcome is `PASS` or `WARN`, update pipeline stage via MCP tool `local-python.state_write_pipeline(stage="semantic-check-complete", details=...)`.

## Outputs

- `artifacts/review/<ticket-id>-semantic-check.md`
- Updated `state/tickets/<ticket-id>/pipeline-status.json` when outcome is `PASS` or `WARN`

## Guardrails

- Never replace conversion mapping notes; add review findings in the semantic check report only.
- Never mark `PASS` when unresolved TODOs or undocumented semantic deviations remain.
- Never advance to `semantic-check-complete` on `FAIL`.
- Preserve traceability to source clauses, rule names, and ticket id in every finding.
- Treat `WARN` as review-visible risk, not as silent success.
