# Semantic Check Report for Ticket 1024325

- Ticket ID: 1024325
- Source CQL: /measures/2026/MIPS/317.cql
- Generated DRL: mips317.drl
- Mapping Document: artifacts/conversion/1024325-mapping.md
- Outcome: FAIL

## Summary

Material semantic drift is present between source CQL intent and generated DRL for MIPS317. The most significant issues are option-family collapse (`G8950_1..G8950_4` to `G8950`), incomplete denominator evidence fan-out (missing BP evidence rows), and reduced not-met logic coverage for `G8952`. Mapping also carries unresolved TODOs around output API shape and option-family expansion. Due to these issues, downstream stages should not continue.

## Clause Coverage

| Extraction Clause / Intent | DRL Rule(s) | Status | Notes |
|---|---|---|---|
| Denominator encounter eligibility + telehealth/modifier/POS exclusions | Year2026.Mips317.Denominator | PASS | Core encounter gate and exclusions are represented. |
| Denominator ExtendedMeasureResultV2 with option_id=all including Denominator Encounter + SBP + DBP evidence | Year2026.Mips317.Denominator.EMR | FAIL | DRL emits denominator candidate rows but does not emit explicit SBP/DBP evidence outputs from source denominator returns. |
| Denominator exclusion G9744 | Year2026.Mips317.Exclusion.G9744.* | WARN | Exclusion present, but overlap/window semantics are simplified relative to source union/interval details. |
| Denominator exception G9745 | Year2026.Mips317.Exception.G9745.* | PASS | Exception path represented with status + EMR split and marker guard. |
| Numerator met G8783 | Year2026.Mips317.Success.G8783.* | WARN | Broadly mapped, but source `last(...)` evidence-selection direction is not preserved explicitly. |
| Numerator met G8950_1, G8950_2, G8950_3, G8950_4 | Year2026.Mips317.Success.G8950.* | FAIL | Four distinct option families collapsed to one `G8950` family; this changes measure behavior and reporting option granularity. |
| Numerator not met G8952 | Year2026.Mips317.NotMet.G8952.* | FAIL | Source union includes derived elevated/hypertensive + not-exists pathways; DRL only checks direct quality-code existence. Also source includes M1279 while DRL uses M1281. |
| Numerator gap G8785 not-exists chain | Year2026.Mips317.Gap.G8785.* | WARN | Not-exists chain exists, but depends on collapsed met family and simplified not-met logic, causing downstream drift. |

## Drift Findings

| Severity | Category | Source Reference | DRL / Mapping Reference | Finding |
|---|---|---|---|---|
| FAIL | option-family collapse | CQL lines 142-343 | Year2026.Mips317.Success.G8950.* | Distinct options `G8950_1..G8950_4` were merged to one `G8950`, changing option-level output semantics. |
| FAIL | missing denominator evidence | CQL lines 56-97 | Year2026.Mips317.Denominator.EMR | Source denominator returns include SBP/DBP evidence (`option_id = all` fan-out), but DRL does not emit corresponding BP evidence rows. |
| FAIL | not-met pathway drift | CQL lines 361-389 | Year2026.Mips317.NotMet.G8952.* and Year2026.Mips317.Gap.G8785.* | Source `G8952` includes derived elevated/hypertensive and compound not-exists pathway; DRL uses narrower direct quality-code checks. |
| FAIL | value-set mismatch | CQL line 366 | Year2026.Mips317.NotMet.G8952.* | Source union includes `MIPS; 497RATE7_PERFORMANCE_NOT_MET_M1279`, but DRL references `...M1281`. |
| WARN | subject/output API mismatch | Plan "Planned EMR API shape" + CQL subject type | mapping intentional deviation section | Plan expects encounter output shape; mapping documents use of `addPatientEMR` and leaves TODO for domain confirmation. |
| WARN | unresolved conversion TODOs | Mapping assumptions/TODO section | artifacts/conversion/1024325-mapping.md | Mapping still contains unresolved TODOs for option-family separation and output API mandate. |

## Required Review Notes

- Subject type consistency: Source is encounter-subject; generated DRL still uses patient-level EMR API with unresolved TODO.
- `option_id = all` fan-out: Literal `all` is not emitted, but denominator fan-out coverage is incomplete (missing SBP/DBP evidence outputs).
- Null/empty parity: No direct tightening found in reviewed predicates, but reduced pathway coverage in `G8952` affects semantic equivalence.
- Comparator parity: BP threshold predicates for `G8783` appear present; however, selection methodology (`last`) parity is not explicit in DRL.
- Earliest/latest selection: Source uses `last(...)`; generated DRL does not preserve explicit selection behavior for key branches.
- Shared dependency status: No unresolved shared-library dependency introduced; issue is logic coverage, not shared dependency.

## Recommendation

- Recommend: Block until fixed
- Reason: Material semantic drift exists in numerator option family behavior, not-met logic, denominator evidence output completeness, and unresolved documented deviations. These are behavior-impacting and exceed WARN tolerance.
