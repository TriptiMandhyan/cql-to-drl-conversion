# Architecture: Local Multi-Agent CQL to DRL Pipeline

## Overview

The workflow is intentionally split into specialist agents with strict stage boundaries.

1. Intake Agent: ticket and metadata retrieval
2. Extractor Agent: CQL parse and semantic extraction
3. Plan Agent: plan creation plus human approval checkpoint
4. Conversion Agent: CQL to DRL transformation
5. PR Agent: PR-ready documentation and checks

## Why This Split

- Better auditability and easier troubleshooting
- Reduced context pressure per agent
- Clear ownership of intermediate artifacts

## Data Flow

- Input: ADO ticket id
- Intermediate: JSON/Markdown artifacts per stage
- Output: DRL files (one per changed CQL), mapping notes, PR draft text

## DRL Modeling Standard

- Conversion output fact modeling must mirror reference DRLs in `examples/drl-reference/year2026/`.
- Prefer platform domain facts (`Program`, `Patient`, `ClinicalActivity`, `EncounterDenominator`, etc.) over synthetic wrapper records.
- Restrict `declare` usage to marker/helper state facts needed for dedup or source splitting.

## Approval Gate

No conversion may start until `state/approval-status.json` is set to:

{
  "ticketId": "<ticket-id>",
  "approved": true,
  "approvedBy": "<name>",
  "approvedAt": "<iso-8601>"
}

## Local First Strategy

This scaffold is local-first. Webhooks and CI agents are deferred until local examples validate quality and reliability.
