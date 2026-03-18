# Local Runbook

## 1) Create ADO PAT

In Azure DevOps:

1. Open User Settings > Personal access tokens.
2. Select New Token.
3. Set organization to `healthcatalyst` and a short expiry window.
4. Scopes minimum needed for this local flow:
	- Work Items: Read
	- Code: Read
5. Create token and copy it once.

## 2) Configure local secret

Set environment variable in your shell session:

```bash
export ADO_PAT="<pat>"
```

Windows persistent equivalent:

```text
setx ADO_PAT "<pat>"
```

## 3) Set ticket URL placeholder

Edit `state/run-input.json` and set:

- `ticketUrl`: `https://dev.azure.com/healthcatalyst/MeasureAble%202.0/_workitems/edit/1024330/`

The intake step will parse ticket description and resolve PR links such as:

- `https://dev.azure.com/healthcatalyst/MeasureAble%202.0/_git/measures/pullrequest/<pr-id>`

The workflow uses PR source branch refs, not main branch, when PR links are present.

## 4) Execute stages with agents

Run stages from Copilot chat using slash agents:

1. `/ticketDescriptionIntakeAgent`
2. `/cql-extractor`
3. `/plan-approval`
4. `/approvalRecorder`
5. `/conversion`
6. `/pr-submission`

## 4.1) Standard non-MCP fallback command

When MCP is preferred but a step needs HTTPS fallback (for example PR iteration changed files and file-at-commit retrieval), use this single script instead of ad-hoc shell snippets:

```bash
python scripts/ado_fallback.py run-extraction --ticket-id <ticket-id>
```

Outputs:

- `artifacts/extraction/<ticket-id>-fetched.json`
- `artifacts/extraction/<ticket-id>.json`
- `artifacts/extraction/raw/<ticket-id>/`

Notes:

- `ADO_PAT` must be set in environment.
- `artifacts/intake/<ticket-id>.json` must exist.
- This script is fallback-only and does not replace MCP-first orchestration.

## 5) Approval gate

Approval is recorded by `/approvalRecorder`.

## 6) Validate outputs

Check for generated files:


Run conversion artifact validation:

```bash
python scripts/validate_conversion_artifacts.py --ticket <ticket-id>
```

Validation now checks naming, EMR fire-once guards, and reference-style fact modeling.

For ticket `1024330`, expect the same files with `1024330` prefix.
