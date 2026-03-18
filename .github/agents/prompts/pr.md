# PR Prompt Module

- Read `artifacts/intake/<ticket-id>.json` for `ticketId`, `ticketUrl`, and `measureHints`.
- Derive `measureNumber` from `measureHints` (e.g. `"MIPS 488"` → `488`).
- Branch name format: `create-{measureNumber}-ab{ticketId}` (e.g. `create-488-ab1048701`).
- Read `githubRepo` settings from `.github/orchestration/config.json` (`owner`, `repo`, `baseBranch`, `drlTargetPath`).
- Using GitHub MCP tools: resolve the base branch SHA, create the new branch, push `artifacts/conversion/mips{measureNumber}.drl` to `drlTargetPath` in that branch.
- PR body must include:
  - Summary of what changed and why.
  - Validation status and unresolved blockers.
  - Reviewer checklist (mapping completeness, rule semantics, assumptions, blockers).
  - ADO work item link formatted as: `ADO Work Item: {ticketUrl}`.
- Create the GitHub pull request and capture the returned PR URL.
- Write `artifacts/pr/<ticket-id>-pr.md` with the summary, GitHub PR URL, and ADO work item link.
