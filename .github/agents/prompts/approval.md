# Approval Prompt Module

- Read `state/pipeline-status.json` and verify stage is `awaiting-approval`.
- Confirm approver identity from user input.
- Update `state/approval-status.json` with `approved: true`, `approvedBy`, and `approvedAt`.
- Update `state/pipeline-status.json` to `conversion-ready`.
- Do not modify ticket id.
