#!/usr/bin/env python3
"""Intake-stage non-MCP Azure DevOps fallback helper.

Purpose:
- Keep MCP as the preferred path for ADO interactions.
- Provide a deterministic fallback for intake-stage gaps only.

Supported operation:
1) Enrich intake artifact cqlPaths from latest PR iteration changed files.

Out of scope by design:
- Extraction-stage raw CQL download
- CQL parsing and extraction artifact generation
- Pipeline stage transitions
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any


ASSUMPTION_TEXT = (
    "Changed CQL paths were enriched using PAT HTTPS fallback for latest PR "
    "iteration changes because this operation is not yet fully covered in MCP."
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _parse_ticket_id_from_url(ticket_url: str) -> str:
    match = re.search(r"/edit/(\d+)", ticket_url)
    if not match:
        raise RuntimeError(f"Could not parse ticket id from ticketUrl: {ticket_url}")
    return match.group(1)


def _infer_ticket_id(explicit_ticket_id: str | None) -> str:
    if explicit_ticket_id:
        return explicit_ticket_id

    run_input_path = Path("state/run-input.json")
    if not run_input_path.exists():
        raise RuntimeError("Ticket id not provided and state/run-input.json not found.")

    run_input = _load_json(run_input_path)

    ticket_id = str(run_input.get("ticketId", "")).strip()
    if ticket_id:
        return ticket_id

    ticket_url = str(run_input.get("ticketUrl", "")).strip()
    if ticket_url:
        return _parse_ticket_id_from_url(ticket_url)

    raise RuntimeError("Could not infer ticket id from state/run-input.json.")


def _auth_header_from_env() -> str:
    pat = os.environ.get("ADO_PAT", "").strip()
    if not pat:
        raise RuntimeError("ADO_PAT environment variable is required for fallback mode.")
    token = base64.b64encode(f":{pat}".encode("ascii")).decode("ascii")
    return f"Basic {token}"


def _http_get_json(url: str, auth_header: str) -> dict[str, Any]:
    req = urllib.request.Request(url)
    req.add_header("Authorization", auth_header)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_latest_iteration_cql_paths(
    project_url: str,
    repository: str,
    pr_id: str,
    auth_header: str,
) -> list[str]:
    iterations_url = (
        f"{project_url}/_apis/git/repositories/{repository}/pullRequests/{pr_id}/iterations"
        "?api-version=7.1"
    )
    iterations_payload = _http_get_json(iterations_url, auth_header)
    iterations = iterations_payload.get("value", [])
    if not iterations:
        return []

    latest_iteration_id = max(int(it.get("id", 0)) for it in iterations)
    changes_url = (
        f"{project_url}/_apis/git/repositories/{repository}/pullRequests/{pr_id}/"
        f"iterations/{latest_iteration_id}/changes?$top=2000&api-version=7.1"
    )
    changes_payload = _http_get_json(changes_url, auth_header)

    return sorted(
        {
            str((entry.get("item") or {}).get("path") or "").strip()
            for entry in changes_payload.get("changeEntries", [])
            if str((entry.get("item") or {}).get("path") or "").lower().endswith(".cql")
        }
    )


def run_intake_enrichment(args: argparse.Namespace) -> int:
    ticket_id = _infer_ticket_id(args.ticket_id)
    intake_path = Path(args.intake) if args.intake else Path(f"artifacts/intake/{ticket_id}.json")
    if not intake_path.exists():
        raise FileNotFoundError(f"Missing intake artifact: {intake_path}")

    intake = _load_json(intake_path)
    project_url = str(intake.get("projectUrl", "")).rstrip("/")
    if not project_url:
        raise RuntimeError("intake.projectUrl is required.")

    resolved_prs = intake.get("resolvedPullRequests", [])
    if not resolved_prs:
        raise RuntimeError("No resolvedPullRequests found in intake artifact.")

    auth_header = _auth_header_from_env()
    merged_paths: set[str] = set(str(p).strip() for p in intake.get("cqlPaths", []) if str(p).strip())

    for row in resolved_prs:
        pr_id = str(row.get("pullRequestId", "")).strip()
        repository = str(row.get("repository", "")).strip()
        if not pr_id or not repository:
            continue

        merged_paths.update(
            _extract_latest_iteration_cql_paths(
                project_url=project_url,
                repository=repository,
                pr_id=pr_id,
                auth_header=auth_header,
            )
        )

    intake["cqlPaths"] = sorted(merged_paths)

    assumptions = intake.get("assumptions", [])
    if not isinstance(assumptions, list):
        assumptions = [str(assumptions)]
    if ASSUMPTION_TEXT not in assumptions:
        assumptions.append(ASSUMPTION_TEXT)
    intake["assumptions"] = assumptions

    output_path = Path(args.out) if args.out else intake_path
    _write_json(output_path, intake)

    print(f"ticketId={ticket_id}")
    print(f"intake={output_path.as_posix()}")
    print(f"cqlPaths={len(intake['cqlPaths'])}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Intake-stage non-MCP Azure DevOps fallback helper.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    enrich_parser = subparsers.add_parser(
        "enrich-intake",
        help="Enrich intake cqlPaths from latest PR iteration changed files.",
    )
    enrich_parser.add_argument(
        "--ticket-id",
        default="",
        help="Ticket id. If omitted, inferred from state/run-input.json.",
    )
    enrich_parser.add_argument(
        "--intake",
        default="",
        help="Path to intake JSON. Default artifacts/intake/<ticket-id>.json",
    )
    enrich_parser.add_argument(
        "--out",
        default="",
        help="Optional output path. Defaults to in-place update of intake JSON.",
    )
    enrich_parser.set_defaults(func=run_intake_enrichment)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as err:  # noqa: BLE001
        print(str(err), file=sys.stderr)
        raise SystemExit(1)
