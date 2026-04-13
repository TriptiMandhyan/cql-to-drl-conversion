# Copilot Custom Agents

These workspace custom agents expose the CQL to DRL pipeline stages in the VS Code Copilot agent picker.

How this is organized:
- Source stage behavior lives in these `.agent.md` files.
- Shared rules and runtime constraints live in `.github/copilot-instructions.md`.
- Stage sequencing and runtime policy live in `.github/orchestration/config.json`.

Expected usage in VS Code:
- Open Chat in Agent mode.
- Select one of the pipeline agents from the picker.
- Provide ticket context (`ticketId` or `ticketUrl`) via prompt or `state/run-input.json`.

Primary agents:
- `cqlFlowOrchestrator`: End-to-end stage coordination with approval gate.
- `ticketDescriptionIntakeAgent`: Ticket normalization and PR/source resolution.
- `cql-extractor`: Structured extraction and plan output.
- `conversion`: DRL generation and clause-to-rule mapping.
- `semanticCheck`: Post-conversion semantic drift review that writes a semantic check report before downstream artifact generation.
- `approvalRecorder`: Explicit approval capture before PR submission.
- `Measure Concept Keeper`: Post-approval concept capture into `MEASURE_CONCEPTS.md` for future developer reuse.
- `apiArtifactBuilder`: local-python MCP auth+data API retrieval into canonical measure JSON artifact.
- `testRunFileBuilder`: Java test file generation following existing year-specific test patterns.
- `pr-submission`: PR draft generation and final stage update.
- `ticketStatusReset`: Ticket reset to baseline state.
- `learningAgent`: Optional non-blocking metrics and pattern aggregation.

Notes:
- Keep agent names stable because slash commands and config references depend on them.
- Keep DRL generation logic in conversion flow and skill files; wrapper metadata should remain orchestration-only.
