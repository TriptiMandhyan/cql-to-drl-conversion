---
name: conversion
description: "Use when plan approval is true and CQL extraction must be converted into DRL with mapping notes."
tools: [read, edit, search]
---

# Conversion Agent

## Purpose

Convert CQL semantics to DRL only after explicit approval, generating one DRL per changed CQL file.

## Inputs

- `state/approval-status.json`
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
3. Read `.github/skills/cql-to-drl/SKILL.md` and `.github/skills/cql-to-drl/cql-to-drl-guide.md` before authoring DRL.
4. For each changed CQL source file in extraction output, generate a corresponding DRL file. Derive the output filename as follows: if the CQL basename already starts with `mips` (case-insensitive), use it as-is with a `.drl` extension; if the basename is a bare number (e.g. `488`), prefix it with `mips` to produce `mips488.drl`. Example: `mips338.cql` → `mips338.drl`; `488.cql` → `mips488.drl`.
5. Use example DRLs from `examples/drl-reference/year2026/` for rule naming style, shared-file handling, and coding patterns when available.
6. Enforce reference-style fact modeling from `.github/skills/cql-to-drl/SKILL.md`; reject synthetic wrapper facts when domain facts are available.
7. Enforce rule naming and marker naming contracts from `.github/skills/cql-to-drl/SKILL.md`; reject ticket-id or sequence-based rule names.
8. Document clause-to-rule mapping and include explicit `Guide Reference` for each mapped rule.
9. Run `python scripts/validate_conversion_artifacts.py --ticket <ticket-id>` and resolve all errors before finalizing outputs.
10. Save DRL and mapping outputs.
11. Update `state/pipeline-status.json` stage to `conversion-complete`.

## Outputs

- `artifacts/conversion/<cql-basename>.drl` (one file per changed CQL)
- `artifacts/conversion/<ticket-id>-mapping.md`

## Guardrails

- Stop immediately if approval is false or missing.
- Preserve traceability to ticket id and source CQL references.
- Do not invent unresolved business rules; mark them as `TODO: needs domain confirmation`.
- Do not output placeholder-only rules such as `eval(true)` unless explicitly marked as blocked with rationale.
- Every generated rule must cite at least one guide section in mapping notes.
- File naming must match changed CQL basenames to preserve source-to-output traceability.
