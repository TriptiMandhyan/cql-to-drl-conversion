# CQL to DRL Mapping: <ticket-id>

## Traceability

- Ticket ID: <ticket-id>
- Source CQL File(s): <path(s)>
- Source Commit(s): <commit-sha(s)>
- Source PR(s): <pr-id(s) or none>
- Extraction Artifact: artifacts/extraction/<ticket-id>.json
- Plan Artifact: artifacts/plan/<ticket-id>.md

## Mapping Table

| CQL Source | DRL Rule | Status | Guide Reference | Notes |
| --- | --- | --- | --- | --- |
| <file>#<definition> | <YearYYYY.<MeasureFamilyPascal>NNN.RuleName> | mapped | <Section X> | <note> |

## Attribution Verification

- Subject type used: <Encounter|Patient>
- EMR API used: <addEncounterEMR|addPatientEMR>
- Output attribution shape implemented: <encounter-scoped only|org only|org+group+provider>
- Plan required attribution shape: <copy from plan>
- Parity check result: <matched|deviation>
- If deviation, explain semantic impact and rationale:
	- <impact>
	- <rationale>

## Assumptions / Gaps

1. <explicit unresolved item and why>
