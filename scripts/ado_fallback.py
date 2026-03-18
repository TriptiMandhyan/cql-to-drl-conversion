#!/usr/bin/env python3
"""General non-MCP Azure DevOps fallback utility.

Purpose:
- Keep MCP as the preferred path for ADO interactions.
- Provide a deterministic fallback for steps that are not currently covered by MCP in this workflow.

Supported fallback operations:
1) Resolve changed CQL files from PR iterations.
2) Fetch CQL source text from PR source commit.
3) Build extraction artifact (definitions/includes/terminology) from fetched CQL.

This script does not infer business logic and does not perform conversion.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ASSUMPTIONS = [
    "MCP was used for PR metadata resolution and source commit enforcement.",
    "HTTPS fallback was used only for latest PR iteration changed files and commit-path file content retrieval.",
    "Extraction is syntax-level and does not infer unstated business logic.",
]


DEFINE_RE = re.compile(
    r'^\s*define\s+(?:function\s+)?(?:"([^"]+)"|([A-Za-z_][A-Za-z0-9_ ]*))\s*(?:\(|:)',
)
INCLUDE_QUOTED_RE = re.compile(
    r'^\s*include\s+"([^"]+)"(?:\s+version\s+\'([^\']+)\')?(?:\s+called\s+([A-Za-z0-9_]+))?',
)
INCLUDE_PLAIN_RE = re.compile(
    r'^\s*include\s+([A-Za-z0-9_\.]+)(?:\s+version\s+\'([^\']+)\')?(?:\s+called\s+([A-Za-z0-9_]+))?',
)
TERM_RE = re.compile(
    r'^\s*(valueset|codesystem|code|concept)\s+"([^"]+)"(?:\s*:\s*\'([^\']+)\')?',
)


@dataclass
class ResolvedPR:
    pr_id: str
    repository: str
    repository_id: str | None
    source_ref: str | None
    source_commit: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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


def _http_get_text(url: str, auth_header: str) -> str:
    req = urllib.request.Request(url)
    req.add_header("Authorization", auth_header)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _infer_ticket_id(explicit_ticket_id: str | None) -> str:
    if explicit_ticket_id:
        return explicit_ticket_id
    pipeline_path = Path("state/pipeline-status.json")
    if not pipeline_path.exists():
        raise RuntimeError("Ticket id not provided and state/pipeline-status.json not found.")
    pipeline = _load_json(pipeline_path)
    ticket_id = str(pipeline.get("ticketId", "")).strip()
    if not ticket_id:
        raise RuntimeError("Could not infer ticket id from state/pipeline-status.json.")
    return ticket_id


def _parse_intake(intake: dict[str, Any]) -> tuple[str, list[ResolvedPR]]:
    project_url = str(intake.get("projectUrl", "")).rstrip("/")
    if not project_url:
        raise RuntimeError("intake.projectUrl is required.")

    resolved_prs = []
    for row in intake.get("resolvedPullRequests", []):
        pr_id = str(row.get("pullRequestId", "")).strip()
        repo = str(row.get("repository", "")).strip()
        source_commit = str(row.get("sourceCommitId", "")).strip()
        if not pr_id or not repo or not source_commit:
            continue
        resolved_prs.append(
            ResolvedPR(
                pr_id=pr_id,
                repository=repo,
                repository_id=(
                    str(row.get("repositoryId")).strip()
                    if row.get("repositoryId") is not None
                    else None
                ),
                source_ref=(
                    str(row.get("sourceRefName")).strip()
                    if row.get("sourceRefName") is not None
                    else None
                ),
                source_commit=source_commit,
            )
        )

    if not resolved_prs:
        raise RuntimeError("No valid resolvedPullRequests found in intake artifact.")
    return project_url, resolved_prs


def _extract_latest_iteration_and_cql_paths(
    project_url: str,
    pr: ResolvedPR,
    auth_header: str,
) -> tuple[int, list[str]]:
    iterations_url = (
        f"{project_url}/_apis/git/repositories/{pr.repository}/pullRequests/{pr.pr_id}/iterations"
        "?api-version=7.1"
    )
    iterations_payload = _http_get_json(iterations_url, auth_header)
    iterations = iterations_payload.get("value", [])
    if not iterations:
        raise RuntimeError(f"No iterations found for PR {pr.pr_id}.")

    latest_iteration = max(int(i.get("id", 0)) for i in iterations)
    changes_url = (
        f"{project_url}/_apis/git/repositories/{pr.repository}/pullRequests/{pr.pr_id}/"
        f"iterations/{latest_iteration}/changes?$top=2000&api-version=7.1"
    )
    changes_payload = _http_get_json(changes_url, auth_header)
    change_entries = changes_payload.get("changeEntries", [])

    cql_paths = sorted(
        {
            str((entry.get("item") or {}).get("path") or "").strip()
            for entry in change_entries
            if str((entry.get("item") or {}).get("path") or "").lower().endswith(".cql")
        }
    )
    if not cql_paths:
        raise RuntimeError(f"No changed CQL files found for PR {pr.pr_id} latest iteration.")

    return latest_iteration, cql_paths


def _safe_raw_filename(cql_path: str) -> str:
    base = Path(cql_path).name
    return base if base else "unknown.cql"


def _fetch_cql_text(
    project_url: str,
    repository: str,
    source_commit: str,
    cql_path: str,
    auth_header: str,
) -> str:
    encoded_path = urllib.parse.quote(cql_path, safe="/")
    # $format=text is the proven retrieval mode from successful runs.
    item_url = (
        f"{project_url}/_apis/git/repositories/{repository}/items"
        f"?path={encoded_path}"
        f"&versionDescriptor.version={source_commit}"
        "&versionDescriptor.versionType=commit"
        "&download=false"
        "&api-version=7.1"
        "&$format=text"
    )
    content = _http_get_text(item_url, auth_header)
    if not content.strip():
        raise RuntimeError(f"No content returned for {cql_path} at commit {source_commit}.")
    return content


def _parse_cql_for_extraction(cql_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    definitions: list[dict[str, Any]] = []
    includes: list[dict[str, Any]] = []
    terminology: list[dict[str, Any]] = []

    for i, line in enumerate(cql_text.splitlines(), start=1):
        d_match = DEFINE_RE.match(line)
        if d_match:
            name = d_match.group(1) if d_match.group(1) else d_match.group(2).strip()
            definitions.append({"name": name, "line": i})

        q_inc = INCLUDE_QUOTED_RE.match(line)
        if q_inc:
            includes.append(
                {
                    "library": q_inc.group(1),
                    "version": q_inc.group(2),
                    "alias": q_inc.group(3),
                    "line": i,
                }
            )
        else:
            p_inc = INCLUDE_PLAIN_RE.match(line)
            if p_inc:
                includes.append(
                    {
                        "library": p_inc.group(1),
                        "version": p_inc.group(2),
                        "alias": p_inc.group(3),
                        "line": i,
                    }
                )

        t_match = TERM_RE.match(line)
        if t_match:
            kind = t_match.group(1).lower()
            name = t_match.group(2)
            raw_id = t_match.group(3)
            identifier = raw_id if raw_id and re.fullmatch(r"\d+(?:\.\d+)+", raw_id) else None
            terminology.append(
                {
                    "kind": kind,
                    "name": name,
                    "identifier": identifier,
                    "line": i,
                }
            )

    return definitions, includes, terminology


def run_extraction_fallback(args: argparse.Namespace) -> int:
    ticket_id = _infer_ticket_id(args.ticket_id)
    intake_path = Path(args.intake) if args.intake else Path(f"artifacts/intake/{ticket_id}.json")
    if not intake_path.exists():
        raise FileNotFoundError(f"Missing intake artifact: {intake_path}")

    intake = _load_json(intake_path)
    project_url, prs = _parse_intake(intake)

    auth_header = _auth_header_from_env()

    raw_dir = Path(args.raw_dir) if args.raw_dir else Path(f"artifacts/extraction/raw/{ticket_id}")
    raw_dir.mkdir(parents=True, exist_ok=True)

    fetched_resolved_prs: list[dict[str, Any]] = []
    extracted_files: list[dict[str, Any]] = []

    for pr in prs:
        latest_iteration, cql_paths = _extract_latest_iteration_and_cql_paths(project_url, pr, auth_header)

        fetched_resolved_prs.append(
            {
                "prId": pr.pr_id,
                "repositoryId": pr.repository_id,
                "repository": pr.repository,
                "sourceRefName": pr.source_ref,
                "sourceCommitId": pr.source_commit,
                "latestIterationId": latest_iteration,
                "changedCqlPaths": cql_paths,
            }
        )

        for cql_path in cql_paths:
            cql_text = _fetch_cql_text(project_url, pr.repository, pr.source_commit, cql_path, auth_header)
            raw_filename = _safe_raw_filename(cql_path)
            raw_path = raw_dir / raw_filename
            raw_path.write_text(cql_text, encoding="utf-8")

            definitions, includes, terminology = _parse_cql_for_extraction(cql_text)
            extracted_files.append(
                {
                    "prId": pr.pr_id,
                    "repository": pr.repository,
                    "path": cql_path,
                    "sourceCommitId": pr.source_commit,
                    "definitions": definitions,
                    "includes": includes,
                    "terminology": terminology,
                }
            )

    fetched_payload = {
        "ticketId": ticket_id,
        "method": "mcp-first-with-https-fallback",
        "resolvedPullRequests": fetched_resolved_prs,
    }
    extraction_payload = {
        "ticketId": ticket_id,
        "sourceType": "pr-changed-cql-files",
        "files": extracted_files,
        "assumptions": ASSUMPTIONS,
        "status": "extraction-complete",
    }

    fetched_path = Path(args.fetched_out) if args.fetched_out else Path(f"artifacts/extraction/{ticket_id}-fetched.json")
    extraction_path = (
        Path(args.extraction_out) if args.extraction_out else Path(f"artifacts/extraction/{ticket_id}.json")
    )
    _write_json(fetched_path, fetched_payload)
    _write_json(extraction_path, extraction_payload)

    print(f"ticketId={ticket_id}")
    print(f"fetched={fetched_path.as_posix()}")
    print(f"extraction={extraction_path.as_posix()}")
    print(f"rawDir={raw_dir.as_posix()}")
    print(f"filesParsed={len(extracted_files)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="General non-MCP Azure DevOps fallback helper for extraction-stage retrieval.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run-extraction",
        help="Fetch changed CQL files and write fetched/extraction artifacts.",
    )
    run_parser.add_argument("--ticket-id", default="", help="Ticket id. If omitted, inferred from state/pipeline-status.json.")
    run_parser.add_argument("--intake", default="", help="Path to intake JSON. Default artifacts/intake/<ticket-id>.json")
    run_parser.add_argument("--raw-dir", default="", help="Raw CQL output directory.")
    run_parser.add_argument("--fetched-out", default="", help="Output path for fetched manifest JSON.")
    run_parser.add_argument("--extraction-out", default="", help="Output path for extraction JSON.")
    run_parser.set_defaults(func=run_extraction_fallback)

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
