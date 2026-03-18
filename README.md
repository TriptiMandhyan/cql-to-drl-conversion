# CQL to DRL Local Multi-Agent Workflow

This project scaffolds a local, VS Code based multi-agent pipeline to automate the flow:

1. Fetch ticket from Azure DevOps (ADO)
2. Pull and inspect CQL source from ADO repo
3. Extract structured information
4. Draft implementation plan
5. Pause for explicit human approval
6. Convert CQL to DRL using project skill guidance
7. Prepare pull request payload for review

## Goals

- Validate the full workflow locally before any webhook or GitHub Actions rollout.
- Keep task ownership split across focused agents with clear handoffs.
- Enforce guardrails around approvals, traceability, and output quality.

## Runtime

- Agent execution is markdown-driven via `.agent.md` files.
- Governance and guardrails are enforced from `.github/orchestration/config.json`.

## MCP-First With Fallback

- MCP remains the preferred integration path wherever applicable.
- For non-MCP extraction retrieval gaps, use `python scripts/ado_fallback.py run-extraction --ticket-id <ticket-id>`.
- Legacy `python scripts/run_extractor.py ...` commands are supported and now delegate to the same fallback utility.

## Suggested Run Order

1. `/ticketDescriptionIntakeAgent`
2. `/cql-extractor`
3. `/plan-approval`
4. `/approvalRecorder`
5. `/conversion`
6. `/pr-submission`

## Project Structure

- `.github/agents/`: Local custom agents (`*.agent.md`)
- `.github/agents/prompts/`: Reusable stage prompt modules used by orchestrator pattern
- `.github/orchestration/config.json`: Lightweight governance and sequencing manifest
- `.github/skills/cql-to-drl/`: Conversion skill and guide
- `.github/`: Workspace guardrails and agent index
- `.vscode/mcp.json`: MCP server configuration for ADO connectivity
- `docs/`: Architecture and runbooks
- `examples/tickets/`: Sample input tickets for dry runs
- `examples/drl-reference/year2026/`: Example DRLs used as style references for naming and coding patterns
- `templates/`: Plan, mapping, and PR templates
- `state/`: Local state and approval artifacts

## Security Notes

- Do not commit real PAT values.
- Use environment variables for secrets.
- Keep generated output traceable back to ticket id and commit SHA.
