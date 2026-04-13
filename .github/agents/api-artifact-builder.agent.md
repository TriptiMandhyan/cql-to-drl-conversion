---
name: apiArtifactBuilder
description: "Use when a measure JSON file must be generated from an authenticated API response before PR submission."
argument-hint: Provide ticket ID context and ensure conversion output exists for measure naming.
tools: [read, edit, search, local-python/*]
---

# API Artifact Builder Agent

## Purpose

Generate a ticket-scoped JSON artifact from an external API response where the access token is retrieved from a separate auth API.

## Inputs

- `state/run-input.json`
- `state/tickets/<ticket-id>/pipeline-status.json`
- `artifacts/intake/<ticket-id>.json`
- `artifacts/review/<ticket-id>-semantic-check.md` (optional when semantic-check gate is disabled)
- `artifacts/conversion/*.drl` (for measure/rate naming)
- `.github/orchestration/config.json` (`apiPayload` section)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Config Contract (`.github/orchestration/config.json`)

`apiPayload` must contain placeholders or real values:

- `enabled`: boolean
- `auth.url`: token endpoint URL
- `auth.method`: `POST` by default
- `auth.headers`: object of static headers (no secrets)
- `auth.bodyTemplate`: request payload template
- `auth.tokenJsonPath`: JSON path to token in auth response
- `data.urlTemplate`: endpoint for data payload (`{ticketId}`, `{measureNumber}`, `{measureYear}`, `{rateNumber}` allowed)
- `data.measureSpecificationFormat`: canonical format for API parameter (example: `26-mips-mips007rate1`)
- `data.measureSlugFormat`: slug pattern used inside `measureSpecification`
- `data.method`: `GET` or `POST`
- `data.headers`: object of static headers (no secrets)
- `data.authorizationFromAuthResponse.tokenJsonPath`: token field name in auth response (`access_token`)
- `data.authorizationFromAuthResponse.headerName`: usually `Authorization`
- `data.authorizationFromAuthResponse.headerValueTemplate`: usually `Bearer {token}`
- `data.outputFilePattern`: default `{measureSlug}.json`

Secrets must come from env vars only:

- `API_AUTH_CLIENT_ID`
- `API_AUTH_CLIENT_SECRET`
- `API_AUTH_SCOPE` (optional)
- `API_AUTH_BASIC_TOKEN`

## Steps

1. Resolve `ticketId` from `state/run-input.json` and read `.github/orchestration/config.json`.
2. If `governance.guardrails.semanticCheckRequiredBeforeApiArtifact` is `true`, confirm stage is `semantic-check-complete`.
3. If `governance.guardrails.semanticCheckRequiredBeforeApiArtifact` is `false`, allow stage `conversion-complete` or `semantic-check-complete`.
4. If semantic check report exists, read it for context. Stop on `FAIL` only when semantic check is required by config.
5. Read intake and conversion artifacts to derive `measureNumber`, `measureYear`, and `rateNumber`.
6. Read `.github/orchestration/config.json::apiPayload`; if required fields are missing, stop with explicit blocker and do not advance stage.
7. Call auth API using configured method/headers/body template and env-var secrets; extract token using `tokenJsonPath`.
8. Call data API with auth header and configured payload/query.
9. Validate response is non-empty JSON payload.
10. Build `measureSpecification` using `data.measureSpecificationFormat` (example: `26-mips-mips007rate1`) and call data API.
11. Write local artifact: `artifacts/pr-assets/<ticket-id>/<measureSlug>.json`.
12. Update pipeline stage via MCP tool: `local-python.state_write_pipeline(stage="api-artifact-ready", details=...)`.

## Outputs

- `artifacts/pr-assets/<ticket-id>/<measure-slug>.json`
- Updated `state/tickets/<ticket-id>/pipeline-status.json`

## Guardrails

- Never persist auth tokens to artifacts or state files.
- Never hardcode credentials or secrets.
- Never continue if API response is empty or non-JSON.
- Always include ticket and source context in `details` when writing stage transition.
- Do not advance if conversion artifacts indicate unresolved DRL correctness blockers (status-vs-EMR gating, marker id fields, or cross-rate attribution scope).
- If `governance.guardrails.semanticCheckRequiredBeforeApiArtifact` is `true`, only run from `semantic-check-complete`.
- If `governance.guardrails.semanticCheckRequiredBeforeApiArtifact` is `false`, allow run from `conversion-complete`.
- Always advance only to `api-artifact-ready`.
- If `measureFamily` is not `mips`, do not apply MIPS-specific slug assumptions; use configured measure-family formats only.
