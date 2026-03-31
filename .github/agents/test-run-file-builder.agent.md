---
name: testRunFileBuilder
description: "Use when a Java test-run file must be generated for the measure before PR submission."
argument-hint: Provide ticket ID context and an optional test template path override.
tools: [read, edit, search, local-python/*]
---

# Test Run File Builder Agent

## Purpose

Generate the measure-specific Java test file required by rules-engine execution, following the structure of an existing year-specific test case.

## Inputs

- `state/run-input.json`
- `state/tickets/<ticket-id>/pipeline-status.json`
- `artifacts/intake/<ticket-id>.json`
- `artifacts/conversion/*.drl`
- `.github/orchestration/config.json` (`testRunFile` section)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

1. Resolve `ticketId` and confirm stage is `api-artifact-ready`.
2. Derive `measureNumber`, `measureYear`, and `rateNumber` from intake/conversion context.
3. Read template test source from `.github/orchestration/config.json::testRunFile.templatePath`.
   - Default: `rules-engine/src/test/java/com/ablehealth/measures/mips/year2026/Year2026Mips047Test.java`
4. Generate target class name from pattern `Year{measureYear}{measureFamilyPascal}{measureNumber}Rate{rateNumber}Test`.
5. Create local output at `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java`.
6. Preserve template style and test structure; only substitute measure/rate-specific identifiers and comments needed for traceability.
7. Update pipeline stage via MCP tool: `local-python.state_write_pipeline(stage="awaiting-approval", details=...)`.

## Outputs

- `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java`
- Updated `state/tickets/<ticket-id>/pipeline-status.json`

## Guardrails

- Never alter unrelated test conventions or package style.
- Never fabricate unknown business logic; mark unresolved specifics as TODO assumptions in the generated file.
- Ensure file name and class name match exactly.
- Do not advance if conversion artifacts carry unresolved DRL quality blockers around status-vs-EMR gating, marker id modeling, or cross-rate attribution scope.
- Only run from `api-artifact-ready` and only advance to `awaiting-approval`.
- Use family-specific naming patterns from config; do not force `Mips` prefix for non-MIPS families.
