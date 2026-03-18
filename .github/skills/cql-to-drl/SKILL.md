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
- `state/approval-status.json`
- `cql-to-drl-guide.md`
- `examples/drl-reference/year2026/*.drl` (if present)

## Required Checks

1. Confirm approval is true before transformation.
2. Confirm extraction artifact contains source references.
3. Confirm ticket id is propagated to outputs.

## Procedure

1. Read extraction clauses and group them by source CQL file.
2. For each changed source CQL file, emit one DRL. If the CQL basename already starts with `mips`, use it as-is (e.g., `mips338.cql` → `mips338.drl`). If the basename is a bare number, prefix with `mips` (e.g., `488.cql` → `mips488.drl`).
3. Keep rule naming deterministic and aligned to patterns in `examples/drl-reference/year2026/*.drl` when available.
4. Enforce rule name contract:
	- Use `Year<year>.Mips<measure>.<PopulationOrOutcome>[.<OptionOrQualifier>][.EMR[.Org|.Group|.Provider]]`.
	- Examples: `Year2026.Mips488.Denominator`, `Year2026.Mips488.Denominator.EMR`, `Year2026.Mips488.Exclusion.M1187.EMR`, `Year2026.Mips488.Success.M1189.EMR.Org`.
	- Do not use ticket-id or sequence-based names such as `1048701_denominator_001`.
5. Enforce marker fact contract for EMR fire-once semantics:
	- Marker declare name format: `Year<year>Mips<measure><Purpose>EMR`.
	- Each EMR-producing rule must include a marker guard and insert marker in `then`.
6. Enforce fact modeling contract aligned to `examples/drl-reference/year2026/*.drl`:
	- Prefer platform domain facts (`Program`, `Patient`, `ClinicalActivity`, `Diagnosis`, `LaboratoryTest`, `EncounterDenominator`) over synthetic wrapper facts.
	- Required DRL header shape for measure files: `import com.ablehealth.model.*`, `import com.ablehealth.payloads.*`, `import com.ablehealth.results.*`, and `global PatientResults controlSet;`.
	- Use `declare` only for marker/helper facts (fire-once dedup or small intermediate facts with 1-2 typed fields).
	- Do not generate generic wrapper declares such as `<Measure>Context`, `<Measure>Evidence`, `<Measure>EmrOutput`.
7. Enforce EMR output semantics:
	- Status rules write status APIs only.
	- EMR rules write EMR APIs only and must preserve org/group/provider attribution behavior from reference DRLs.
	- For option `all` denominator patterns, include all required ExtendedMeasureResultV2 evidence outputs.
8. Emit DRL in package structure expected by target repository and preserve shared-file handling conventions from examples.
9. Generate mapping document that links each CQL clause to DRL rule ids.
10. Flag unsupported constructs and assumptions.
11. Run `python scripts/validate_conversion_artifacts.py --ticket <ticket-id>` and fix violations before finalizing outputs.

## Outputs

- `artifacts/conversion/<cql-basename>.drl` (one file per changed CQL)
- `artifacts/conversion/<ticket-id>-mapping.md`

## Non-Negotiable Guardrails

- Never run if approval is false.
- Never hide ambiguity; write explicit assumption notes.
- Never omit source CQL file and expression references.
- Never mix ticket id in rule names or marker names.
- Never skip EMR marker guards for append-style outputs.
- Never introduce synthetic measure wrapper facts when equivalent platform domain facts exist.
