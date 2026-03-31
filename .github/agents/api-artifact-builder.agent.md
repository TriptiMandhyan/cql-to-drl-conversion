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

1. Resolve `ticketId` from `state/run-input.json` and confirm current stage is `conversion-complete`.
2. Read intake and conversion artifacts to derive `measureNumber`, `measureYear`, and `rateNumber`.
3. Read `.github/orchestration/config.json::apiPayload`; if required fields are missing, stop with explicit blocker and do not advance stage.
4. Call auth API using configured method/headers/body template and env-var secrets; extract token using `tokenJsonPath`.
5. Call data API with auth header and configured payload/query.
6. Validate response is non-empty JSON payload.
7. Build `measureSpecification` using `data.measureSpecificationFormat` (example: `26-mips-mips007rate1`) and call data API.
8. Write local artifact: `artifacts/pr-assets/<ticket-id>/<measureSlug>.json`.
9. Update pipeline stage via MCP tool: `local-python.state_write_pipeline(stage="api-artifact-ready", details=...)`.

## Outputs

- `artifacts/pr-assets/<ticket-id>/<measure-slug>.json`
- Updated `state/tickets/<ticket-id>/pipeline-status.json`

## Guardrails

- Never persist auth tokens to artifacts or state files.
- Never hardcode credentials or secrets.
- Never continue if API response is empty or non-JSON.
- Always include ticket and source context in `details` when writing stage transition.
- Do not advance if conversion artifacts indicate unresolved DRL correctness blockers (status-vs-EMR gating, marker id fields, or cross-rate attribution scope).
- Only run from `conversion-complete` and only advance to `api-artifact-ready`.
- If `measureFamily` is not `mips`, do not apply MIPS-specific slug assumptions; use configured measure-family formats only.
