# Semantic Check Report for Ticket <ticket-id>

- Ticket ID: <ticket-id>
- Source CQL: <source-cql-path-or-paths>
- Generated DRL: <measure-slug>.drl
- Mapping Document: artifacts/conversion/<ticket-id>-mapping.md
- Outcome: PASS | WARN | FAIL

## Summary

- One paragraph summary of semantic preservation confidence and major review outcome.

## Clause Coverage

| Extraction Clause / Intent | DRL Rule(s) | Status | Notes |
|---|---|---|---|
| <clause> | <rules> | PASS/WARN/FAIL | <coverage note> |

## Drift Findings

| Severity | Category | Source Reference | DRL / Mapping Reference | Finding |
|---|---|---|---|---|
| WARN | option-family | <source lines> | <rule names> | <finding> |

## Required Review Notes

- Subject type consistency:
- `option_id = all` fan-out:
- Null/empty parity:
- Comparator parity:
- Earliest/latest selection:
- Shared dependency status:

## Recommendation

- Recommend: Proceed | Proceed with caution | Block until fixed
- Reason:
