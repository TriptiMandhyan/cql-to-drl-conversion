# PR Draft: <ticket-id>

## Summary

- Ticket: <ticket-id>
- Scope: CQL to DRL conversion

## Included Artifacts

- DRLs (one per changed CQL, canonical naming): `artifacts/conversion/<measure-slug>.drl`
- Mapping: `artifacts/conversion/<ticket-id>-mapping.md`
- API JSON: `artifacts/pr-assets/<ticket-id>/<measure-slug>.json`
- Test Run File: `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java`
- Plan: `artifacts/plan/<ticket-id>.md`
- DRL reference patterns: `examples/drl-reference/year2026/*.drl` (if available)

## Validation

- Local checks run: <yes/no>
- Result: <pass/fail/partial>
- Notes: <details>

## Risks and Follow-ups

- <risk>

## Reviewer Checklist

- Mapping completeness
- Rule semantics preserved
- Assumptions acceptable
- Blockers documented
