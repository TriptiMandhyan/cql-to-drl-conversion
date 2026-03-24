---
name: pr-submission
description: "Use when conversion is complete and a pull request draft with validation summary must be generated."
argument-hint: Provide ticket ID context and ensure conversion artifacts are present.
tools: [read, edit, github/*, local-python/*]
---

# PR Submission Agent

## Purpose

Create a GitHub branch, open a pull request against the target rules-engine repository, and produce local PR documentation for reviewer handoff.

## Inputs

- `artifacts/conversion/mips<measure-number>.drl` (one file per changed CQL)
- `artifacts/conversion/<ticket-id>-mapping.md`
- `artifacts/intake/<ticket-id>.json`
- `templates/pr-template.md`
- `.github/orchestration/config.json` (contains `githubRepo` settings)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

1. Read `.github/orchestration/config.json` and enforce traceability guardrails. Retrieve `githubRepo.owner`, `githubRepo.repo`, and `githubRepo.baseBranch`.
2. Read `artifacts/intake/<ticket-id>.json` to obtain `ticketId` and `measureHints` (to derive `measureNumber`, e.g. `"MIPS 488"` → `488`).
3. Derive branch name: `create-{measureNumber}-ab{ticketId}` (example: `create-488-ab1048701`).
4. Using GitHub MCP tools:
   a. Resolve the SHA of `githubRepo.baseBranch` (default branch, typically `main`).
   b. Create the branch `create-{measureNumber}-ab{ticketId}` at that SHA in `{owner}/{repo}`.
   c. Push (create/update) each converted DRL file from `artifacts/conversion/mips{measureNumber}.drl` into the branch under the path configured in `githubRepo.drlTargetPath`.
5. Compose PR body:
   - Summary of conversion scope and impacted areas.
   - Validation results and known blockers.
   - Reviewer checklist.
   - Link to ADO work item: use `ticketUrl` from the intake artifact (format: `ADO Work Item: <ticketUrl>`).
6. Create the GitHub pull request from branch `create-{measureNumber}-ab{ticketId}` targeting `githubRepo.baseBranch`.
7. Summarize conversion scope, include the GitHub PR URL, and write the local PR draft artifact.
8. Update pipeline stage via MCP tool `local-python.state_write_pipeline(stage="pr-ready", details=...)`.

## Outputs

- `artifacts/pr/<ticket-id>-pr.md` (local draft including GitHub PR URL)
- GitHub branch: `create-{measureNumber}-ab{ticketId}` in `AbleHealth/rules-engine`
- GitHub pull request in `AbleHealth/rules-engine`

## Guardrails

- Include ticket id, ADO work item URL, and source commit references in the PR body.
- Never claim validation passed if checks were not run.
- Keep unresolved risks explicit.
- Do not store GitHub tokens in any artifact file; use `GITHUB_TOKEN` environment variable only.
- Pipeline state writes must use MCP state tools (`local-python.state_write_pipeline`), not direct file edits.
