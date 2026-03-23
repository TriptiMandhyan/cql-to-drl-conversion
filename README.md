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
- Local helper execution is exposed through a FastAPI-hosted MCP server (`local-python`) at `http://127.0.0.1:8765/mcp`.
- For intake-stage non-MCP gaps (changed CQL paths from PR iteration changes), use MCP tool `local-python.enrich_intake`.
- For extraction-stage non-MCP gaps (commit-pinned raw CQL retrieval), use MCP tool `local-python.fetch_raw_cql`.
- State read/write operations can be routed through MCP tools backed by `scripts/state_manager.py` (`state_read_pipeline`, `state_write_pipeline`, `state_read_approval`, `state_write_approval`).
- Full first-time ticket cleanup can be run via MCP tool `local-python.state_reset_ticket_baseline`.
- Helper scripts are fetch-only utilities. Agents remain responsible for parsing, artifact generation, and stage transitions.

## Local MCP Server Setup

```powershell
python -m pip install -r config/mcp/requirements-local-mcp.txt
python scripts/local_mcp_server.py
```

## State Directory Setup

Before running agents, create the ticket state directory:

```powershell
mkdir -p state/tickets
```

This ensures each ticket's per-ticket state folder (`state/tickets/<ticket-id>/`) can be created by agents as they run.

## Suggested Run Order

1. `/ticketDescriptionIntakeAgent`
2. `/cql-extractor`
3. `/approvalRecorder` (single call with approver details)
4. `/conversion`
5. `/pr-submission`

## Utility Command

- `/ticketStatusReset` resets the current ticket state to `intake-start` and clears approval so the flow can be re-run.

## Canonical Status Values

- Pipeline and approval statuses are standardized in `.github/orchestration/statuses.json`.
- `scripts/state_manager.py` enforces allowed pipeline stage values through `PipelineStage` enum.

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
