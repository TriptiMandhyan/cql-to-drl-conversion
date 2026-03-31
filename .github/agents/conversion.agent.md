---
name: conversion
description: "Use when extraction is complete and CQL artifacts must be converted into DRL with mapping notes."
argument-hint: Provide ticket ID context and confirm extraction/plan artifacts are present.
tools: [read, edit, search, local-python/*]
---

# Conversion Agent

## Purpose

Convert CQL semantics to DRL after extraction is complete, generating one DRL per changed CQL file.

## Inputs

- `state/run-input.json`
- `artifacts/extraction/<ticket-id>.json`
- `artifacts/plan/<ticket-id>.md`
- `.github/skills/cql-to-drl/SKILL.md`
- `.github/skills/cql-to-drl/cql-to-drl-guide.md`
- `examples/drl-reference/year2026/*.drl` (if present)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.
- `governance.guardrails.guideReferenceRequiredInMapping` must be enforced.
- `governance.guardrails.blockPlaceholderOnlyDrl` must be enforced.

## DRL Quality Rules (Carry-Forward)

Apply these rules to every generated DRL before writing conversion outputs:

1. GAP status rules must not be gated by EMR evidence-marker facts. GAP must depend on status predicates or dedicated status marker facts emitted by status rules.
2. If Group/Provider marker facts are filtered by `groupId` or `providerId`, the declared fact type must include those fields and inserts must populate them.
3. Cross-rate exclusions for group/provider logic must be attribution-scoped (same group/provider tuple) unless patient-global behavior is explicitly documented as an approved deviation.
4. Any EMR evidence predicate reused for status gating must be predicate-equivalent to the status rule for timing windows and modifier logic.
5. Do not finalize conversion if declared fact fields referenced in rule constraints are missing from `declare` blocks.

## Steps

1. Read `.github/orchestration/config.json` and enforce conversion guardrails.
2. Read `.github/skills/cql-to-drl/SKILL.md` and `.github/skills/cql-to-drl/cql-to-drl-guide.md` before authoring DRL, and treat them as a conversion checklist rather than background context.
4. For each changed CQL source file in extraction output, select at least one matching reference DRL from `examples/drl-reference/year2026/` or an approved production artifact and compare it for:
	- org/group/provider EMR attribution loops
	- split `.Org` versus `.GroupAndProvider` status rules when present
	- EMR salience and marker placement
	- earliest versus latest accumulate direction
	- shared-library dependency usage and naming
	- clinically meaningful rule naming and option-id preservation
	- option-all fan-out behavior (concrete option-code rows versus literal `all`)
5. For each changed CQL source file in extraction output, generate exactly one corresponding DRL file using measure-family naming from runtime config (`measureSlug` contract). Do not emit duplicate aliases for the same source CQL file.
6. Use example DRLs from `examples/drl-reference/year2026/` for rule naming style, shared-file handling, coding patterns, and parity checks when available.
7. Enforce reference-style fact modeling from `.github/skills/cql-to-drl/SKILL.md`; reject synthetic wrapper facts when domain facts are available.
8. Enforce rule naming and marker naming contracts from `.github/skills/cql-to-drl/SKILL.md`; reject ticket-id or sequence-based rule names.
9. Before validation, manually check the generated DRL for the following semantic-preservation requirements:
	- EMR rules preserve org/group/provider attribution when the reference DRL does.
	- Status rules preserve org/group/provider coverage and keep split org versus group/provider structure when the reference DRL does.
	- GAP rules are derived from status truth, not EMR evidence side effects.
	- Group/provider marker declarations and inserts carry attribution ids (`groupId`, `providerId`) when those ids are used in constraints.
	- Cross-rate exclusions for group/provider are scoped to matching attribution ids unless an approved patient-global design is documented.
	- EMR evidence predicates match the corresponding status predicates when used for gating logic.
	- Null-or-empty predicates remain logically equivalent to the source CQL and reference DRL.
	- Earliest versus latest accumulation matches source intent or documented reference parity.
	- Shared-library queries/facts are reused exactly or documented as unresolved.
	- Each CQL `option_id = all` clause is expanded to concrete option-code EMR rows and does not output literal `all` as option id.
10. Document clause-to-rule mapping and include explicit `Guide Reference` for each mapped rule.
11. In mapping notes, record any intentional deviation from the reference DRL structure, including attribution strategy, shared dependencies, salience, accumulate direction, or naming.
12. Call MCP tool `local-python.validate_conversion_artifacts(ticket_id)` and resolve all errors before finalizing outputs.
13. Save DRL and mapping outputs.
14. Update pipeline stage via MCP tool `local-python.state_write_pipeline(stage="conversion-complete", details=...)`.

## Outputs

- `artifacts/conversion/<measure-slug>.drl` (one file per changed CQL)
- `artifacts/conversion/<ticket-id>-mapping.md`

## Guardrails

- Preserve traceability to ticket id and source CQL references.
- Do not invent unresolved business rules; mark them as `TODO: needs domain confirmation`.
- Do not output placeholder-only rules such as `eval(true)` unless explicitly marked as blocked with rationale.
- Every generated rule must cite at least one guide section in mapping notes.
- File naming must use canonical `<measure-slug>.drl` and emit only one DRL per changed CQL source.
- MIPS-specific naming/rule conventions apply only when `measureFamily == mips`; for non-MIPS families, use family-specific conventions defined by config and source semantics.
- Pipeline state writes must use MCP state tools (`local-python.state_write_pipeline`), not direct file edits.
- Validation is not complete until attribution loops, status fan-out, null-handling fidelity, accumulate direction, shared dependencies, and option-all fan-out behavior have been checked against the chosen reference DRL.
- Validation is not complete until attribution loops, status fan-out, null-handling fidelity, accumulate direction, shared dependencies, option-all fan-out behavior, cross-rate attribution scope, and status-vs-EMR predicate parity have been checked against the chosen reference DRL.
- If the generated DRL intentionally deviates from the reference structure, the deviation must be documented in mapping notes before finalization.
