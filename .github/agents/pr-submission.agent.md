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

- `artifacts/conversion/<measure-slug>.drl` (one file per changed CQL; family-specific slug)
- `artifacts/conversion/<ticket-id>-mapping.md`
- `artifacts/pr-assets/<ticket-id>/<measure-slug>.json`
- `artifacts/pr-assets/<ticket-id>/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java`
- `artifacts/intake/<ticket-id>.json`
- `templates/pr-template.md`
- `.github/orchestration/config.json` (contains `githubRepo` settings)

## Runtime Config Guardrails

- `governance.enabled` must be `true`.
- `governance.guardrails.slashOnlyExecution` must be enforced.
- `governance.guardrails.approvalRequiredBeforePrSubmission` must be enforced.
- `governance.guardrails.ticketTraceabilityRequired` must be enforced.

## Steps

1. Read `.github/orchestration/config.json` and enforce traceability guardrails. Retrieve `githubRepo.owner`, `githubRepo.repo`, `githubRepo.baseBranch`, `githubRepo.branchPattern`, and `githubRepo.drlTargetPath`.
2. Read `state/tickets/<ticket-id>/pipeline-status.json` and validate stage is `pr-ready`.
3. Read `state/tickets/<ticket-id>/approval-status.json` and validate `approved=true` for the current run before any GitHub operation.
4. Read `artifacts/intake/<ticket-id>.json` to obtain `ticketId`, `measureHints`, and `cqlPaths`.
5. Derive identifiers:
   a. `measureFamily` from intake/paths/config (`mips`, `ecqm`, `hedis`, etc.).
   b. `measureNumber` from `measureHints` or CQL basename.
   c. `measureYear` from CQL paths.
6. Derive `rateNumber` from conversion basename when applicable (rate-based measures only).
7. Derive branch name from `githubRepo.branchPattern` using family-aware placeholders.
8. If the derived branch already exists, reuse it. Only create it from base-branch SHA when it does not exist.
9. Using GitHub MCP tools:
   a. Resolve the SHA of `githubRepo.baseBranch` (default branch, typically `main`).
   b. Create the derived branch at that SHA in `{owner}/{repo}` only if step 6 determined the branch does not already exist.
   c. Build destination directory dynamically as `{githubRepo.drlTargetPath}/{measureFamilyLower}/year{measureYear}`. Do not hardcode family segments in agent logic.
   d. Push (create/update) each converted DRL file from `artifacts/conversion/*.drl` for the current ticket into that destination directory.
   e. Push the generated JSON artifact into `githubRepo.jsonTargetPath` with canonical name `{measureSlug}.json`.
   f. Push the generated Java test file into `githubRepo.testTargetPath` with canonical class file name `Year{measureYear}{measureFamilyPascal}{measureNumber}Rate{rateNumber}Test.java`.
10. Compose PR body:
   - Summary of conversion scope and impacted areas.
   - Summary of supplemental JSON and test artifact additions.
   - Validation results and known blockers.
   - DRL non-regression checklist confirmation (status-vs-EMR gating, marker id fields, cross-rate attribution scope, predicate parity).
   - Reviewer checklist.
   - Link to ADO work item: use `ticketUrl` from the intake artifact (format: `ADO Work Item: <ticketUrl>`).
11. Create the GitHub pull request from the derived branch targeting `githubRepo.baseBranch`.
12. Summarize conversion scope, include the GitHub PR URL, and write the local PR draft artifact.
13. Update pipeline stage via MCP tool `local-python.state_write_pipeline(stage="pr-submitted", details=...)`.

## Outputs

- `artifacts/pr/<ticket-id>-pr.md` (local draft including GitHub PR URL)
- GitHub branch: from `githubRepo.branchPattern` using family-aware placeholders
- GitHub JSON file: `githubRepo.jsonTargetPath/<measure-slug>.json`
- GitHub test file: `githubRepo.testTargetPath/Year<measureYear><measureFamilyPascal><measureNumber>Rate<rateNumber>Test.java`
- GitHub pull request in `AbleHealth/rules-engine`

## Guardrails

- Include ticket id, ADO work item URL, and source commit references in the PR body.
- Never claim validation passed if checks were not run.
- Keep unresolved risks explicit.
- Do not store GitHub tokens in any artifact file; use `GITHUB_TOKEN` environment variable only.
- Pipeline state writes must use MCP state tools (`local-python.state_write_pipeline`), not direct file edits.
- Only ticket-scoped DRL, JSON, and Java test artifacts may be committed in PR submission stage.
- JSON and Java test artifacts must come only from `artifacts/pr-assets/<ticket-id>/` for the current ticket.
- Destination path must be year-aware under `.../measure/{measureFamilyLower}/year<measureYear>`.
- Do not open/update PR until conversion artifacts explicitly document that GAP is not EMR-marker-gated, attribution marker ids are modeled correctly, and cross-rate exclusions are attribution-scoped (or approved as patient-global).
- If conversion guidance is MIPS-specific, apply it only when `measureFamily == mips`; require family-specific rules for other families.
