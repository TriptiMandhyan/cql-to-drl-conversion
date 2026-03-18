# Agent Protocol (Adapted)

## Intent

Define shared behavior for all slash agents in this repository.

## Protocol

1. Read `state/pipeline-status.json` before writing outputs.
2. Read stage input artifact from previous phase.
3. Write only stage-owned artifact files.
4. Update `state/pipeline-status.json` with new stage and timestamp.
5. Preserve ticket id, source refs, and source file paths.
6. If helper utilities are used, use them for fetch/IO only; keep policy decisions in agent instructions.

## Guardrails

- Never proceed to conversion when approval is false.
- Never use main branch when PR source refs are available.
- Never write secrets to artifacts.
- Mark unresolved logic as assumptions or blockers.
- Do not let helper scripts update stage transitions on behalf of the agent.
- Conversion outputs must use reference-style fact modeling (platform domain facts and minimal marker/helper declares).
