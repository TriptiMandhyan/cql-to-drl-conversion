---
name: conversion
description: "Use when plan approval is true and CQL extraction must be converted into DRL with mapping notes."
tools: [read, edit, search, local-python/*]
---

# Conversion Agent

## Purpose

Convert CQL semantics to DRL only after explicit approval, generating one DRL per changed CQL file.

## Inputs

- `state/run-input.json`
- `state/tickets/<ticket-id>/approval-status.json`
- `artifacts/extraction/<ticket-id>.json`
- `artifacts/plan/<ticket-id>.md`
- `.github/skills/cql-to-drl/SKILL.md`
- `.github/skills/cql-to-drl/cql-to-drl-guide.md`
- `examples/drl-reference/year2026/*.drl` (if present)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.approvalRequiredBeforeConversion` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.
- `governance.guardrails.guideReferenceRequiredInMapping` must be enforced.
- `governance.guardrails.blockPlaceholderOnlyDrl` must be enforced.

## Steps

1. Read `.github/orchestration/config.json` and enforce conversion guardrails.
2. Validate `approved` is true in approval state.
3. Read `.github/skills/cql-to-drl/SKILL.md` and `.github/skills/cql-to-drl/cql-to-drl-guide.md` before authoring DRL, and treat them as a conversion checklist rather than background context.
4. For each changed CQL source file in extraction output, select at least one matching reference DRL from `examples/drl-reference/year2026/` or an approved production artifact and compare it for:
	- org/group/provider EMR attribution loops
	- split `.Org` versus `.GroupAndProvider` status rules when present
	- EMR salience and marker placement
	- earliest versus latest accumulate direction
	- shared-library dependency usage and naming
	- clinically meaningful rule naming and option-id preservation
	- option-all fan-out behavior (concrete option-code rows versus literal `all`)
5. For each changed CQL source file in extraction output, generate exactly one corresponding DRL file using canonical MIPS naming. Derive the output filename as follows: if the CQL basename already starts with `mips` (case-insensitive), normalize to lowercase `mips` and use it with a `.drl` extension; if the basename is a bare number (e.g. `488` or `050`), prefix it with `mips` to produce `mips488.drl` or `mips050.drl`. Do not also emit a basename-only file such as `488.drl` or `050.drl`.
6. Use example DRLs from `examples/drl-reference/year2026/` for rule naming style, shared-file handling, coding patterns, and parity checks when available.
7. Enforce reference-style fact modeling from `.github/skills/cql-to-drl/SKILL.md`; reject synthetic wrapper facts when domain facts are available.
8. Enforce rule naming and marker naming contracts from `.github/skills/cql-to-drl/SKILL.md`; reject ticket-id or sequence-based rule names.
9. Before validation, manually check the generated DRL for the following semantic-preservation requirements:
	- EMR rules preserve org/group/provider attribution when the reference DRL does.
	- Status rules preserve org/group/provider coverage and keep split org versus group/provider structure when the reference DRL does.
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

- `artifacts/conversion/mips<measure-number>.drl` (one file per changed CQL)
- `artifacts/conversion/<ticket-id>-mapping.md`

## Guardrails

- Stop immediately if approval is false or missing.
- Preserve traceability to ticket id and source CQL references.
- Do not invent unresolved business rules; mark them as `TODO: needs domain confirmation`.
- Do not output placeholder-only rules such as `eval(true)` unless explicitly marked as blocked with rationale.
- Every generated rule must cite at least one guide section in mapping notes.
- File naming must use canonical `mips<measure-number>.drl` and emit only one DRL per changed CQL source.
- Pipeline state writes must use MCP state tools (`local-python.state_write_pipeline`), not direct file edits.
- Validation is not complete until attribution loops, status fan-out, null-handling fidelity, accumulate direction, shared dependencies, and option-all fan-out behavior have been checked against the chosen reference DRL.
- If the generated DRL intentionally deviates from the reference structure, the deviation must be documented in mapping notes before finalization.
