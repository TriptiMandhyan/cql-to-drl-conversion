---
name: cql-to-drl
description: "Use when converting approved CQL extraction artifacts into DRL and generating a clause-to-rule mapping."
---

# CQL to DRL Skill

## Objective

Transform extracted CQL semantics into DRL in a traceable and reviewable format.

## Required Inputs

- `artifacts/extraction/<ticket-id>.json`
- `artifacts/plan/<ticket-id>.md`
- `state/tickets/<ticket-id>/approval-status.json`
- `cql-to-drl-guide.md`
- `examples/drl-reference/year2026/*.drl` (if present)

## Required Checks

1. Confirm approval is true before transformation.
2. Confirm extraction artifact contains source references.
3. Confirm ticket id is propagated to outputs.
4. Confirm the chosen reference DRL patterns for attribution, salience, marker placement, and status fan-out are identified before authoring rules.
5. Confirm null/empty predicate semantics from the source clause are preserved in the DRL translation.
6. Confirm earliest vs latest accumulate direction is justified from CQL intent or reference DRL parity.
7. Confirm any shared-library query or fact dependency is either known to exist or explicitly documented as unresolved.
8. Confirm every CQL `option_id = all` clause fans out to concrete option-code EMR rows and never emits literal `all` as an EMR option id.

## Procedure

1. Read extraction clauses and group them by source CQL file.
2. For each changed source CQL file, emit one DRL. If the CQL basename already starts with `mips`, use it as-is (e.g., `mips338.cql` → `mips338.drl`). If the basename is a bare number, prefix with `mips` (e.g., `488.cql` → `mips488.drl`).
3. Keep rule naming deterministic and aligned to patterns in `examples/drl-reference/year2026/*.drl` when available.
4. Before authoring rules, compare the source clause against at least one matching reference DRL for:
	- org/group/provider attribution loops
	- split `.Org` versus `.GroupAndProvider` status rules when present
	- EMR rule salience and fire-once marker placement
	- earliest versus latest accumulate direction
	- shared-library dependency usage
5. Enforce rule name contract:
	- Use `Year<year>.Mips<measure>.<PopulationOrOutcome>[.<OptionOrQualifier>][.EMR[.Org|.Group|.Provider]]`.
	- Examples: `Year2026.Mips488.Denominator`, `Year2026.Mips488.Denominator.EMR`, `Year2026.Mips488.Exclusion.M1187.EMR`, `Year2026.Mips488.Success.M1189.EMR.Org`.
	- Do not use ticket-id or sequence-based names such as `1048701_denominator_001`.
6. Enforce marker fact contract for EMR fire-once semantics:
	- Marker declare name format: `Year<year>Mips<measure><Purpose>EMR`.
	- Each EMR-producing rule must include a marker guard and insert marker in `then`.
7. Enforce fact modeling contract aligned to `examples/drl-reference/year2026/*.drl`:
	- Prefer platform domain facts (`Program`, `Patient`, `ClinicalActivity`, `Diagnosis`, `LaboratoryTest`, `EncounterDenominator`) over synthetic wrapper facts.
	- Required DRL header shape for measure files: `import com.ablehealth.model.*`, `import com.ablehealth.payloads.*`, `import com.ablehealth.results.*`, and `global PatientResults controlSet;`.
	- Use `declare` only for marker/helper facts (fire-once dedup or small intermediate facts with 1-2 typed fields).
	- Do not generate generic wrapper declares such as `<Measure>Context`, `<Measure>Evidence`, `<Measure>EmrOutput`.
8. Enforce EMR output semantics:
	- Status rules write status APIs only.
	- EMR rules write EMR APIs only and must preserve org/group/provider attribution behavior from reference DRLs.
	- When a production/reference DRL splits status behavior into `.Org` plus `.GroupAndProvider`, preserve that structure unless mapping notes explain an equivalent alternative.
	- If EMR output is encounter-based, emit org (`""`), each group id, and provider id when present; do not silently drop group/provider copies.
	- For option `all` denominator patterns, include all required ExtendedMeasureResultV2 evidence outputs.
	- Treat `option_id = all` as expansion semantics: emit concrete option-code rows (for example `G9694`, `0509F`, `0509F-8P`) and never emit option id `all` in `addPatientEMR`.
9. Enforce semantic-preservation rules:
	- Preserve OR-vs-AND logic shape for null/empty predicates.
	- Preserve punctuation and business meaning in option ids and clinically meaningful rule suffixes when reference DRLs use them.
	- Do not switch earliest/ latest evidence selection without explicit justification.
10. Emit DRL in package structure expected by target repository and preserve shared-file handling conventions from examples.
11. Generate mapping document that links each CQL clause to DRL rule ids.
12. In mapping notes, explicitly record any intentional deviation from the reference DRL structure, including attribution strategy, naming, salience, shared dependencies, or accumulate direction.
13. In mapping notes for any `option_id = all` clause, list the concrete option-code set used for EMR fan-out.
14. Flag unsupported constructs and assumptions.
15. Call MCP tool `local-python.validate_conversion_artifacts(ticket_id)` and fix violations before finalizing outputs.

## Outputs

- `artifacts/conversion/mips<measure-number>.drl` (one file per changed CQL)
- `artifacts/conversion/<ticket-id>-mapping.md`

## Non-Negotiable Guardrails

- Never run if approval is false.
- Never hide ambiguity; write explicit assumption notes.
- Never omit source CQL file and expression references.
- Never mix ticket id in rule names or marker names.
- Never skip EMR marker guards for append-style outputs.
- Never introduce synthetic measure wrapper facts when equivalent platform domain facts exist.
- Never drop group/provider EMR attribution or group/provider status propagation when the reference DRL includes them.
- Never rewrite null-or-empty source logic into a stricter predicate.
- Never change earliest-versus-latest evidence selection without documenting why the new direction is correct.
- Never invent local stand-ins for unresolved shared-library queries or facts.
- Never emit literal `all` as an EMR option id when CQL uses `option_id = all`; always fan out to concrete option codes.
