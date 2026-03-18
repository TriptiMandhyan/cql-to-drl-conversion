#!/usr/bin/env python3
"""Extraction-stage non-MCP Azure DevOps fallback helper.

Purpose:
- Keep MCP as the preferred path for ADO interactions.
- Provide a deterministic fallback for extraction-stage gaps only.

Supported operations:
1) Fetch raw CQL file contents from authoritative intake cqlPaths at a PR source commit.
2) Fetch raw CQL file contents and build normalized extraction JSON.

Out of scope by design:
- Ticket and PR metadata resolution
- PR iteration changed-file discovery
- Pipeline stage transitions
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
from pathlib import Path
from typing import Any


ASSUMPTIONS = [
    "MCP was used for PR metadata resolution and source commit enforcement.",
    "HTTPS fallback was used only for latest PR iteration changed files and commit-path file content retrieval.",
    "Extraction is syntax-level and does not infer unstated business logic.",
]


INCLUDE_RE = re.compile(
    r'^\s*include\s+"([^"]+)"(?:\s+version\s+(?:\'([^\']+)\'|"([^"]+)"))?\s+called\s+([A-Za-z_][A-Za-z0-9_]*)',
    re.IGNORECASE,
)
DEFINE_RE = re.compile(
    r'^\s*define\s+(?:function\s+)?"([^"]+)"(?:\s*\([^)]*\))?\s*:?',
    re.IGNORECASE,
)
TERMINOLOGY_RE = re.compile(
    r'^\s*(valueset|codesystem|code|concept)\s+"([^"]+)"(?:\s*:\s*(?:\'([^\']+)\'|"([^"]+)"))?',
    re.IGNORECASE,
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


def _http_get_bytes(url: str, auth_header: str) -> bytes:
    req = urllib.request.Request(url)
    req.add_header("Authorization", auth_header)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _build_item_url(project_url: str, repository: str, path: str, commit_id: str) -> str:
    encoded_path = urllib.parse.quote(path, safe="/")
    encoded_commit = urllib.parse.quote(commit_id, safe="")
    return (
        f"{project_url}/_apis/git/repositories/{repository}/items"
        f"?path={encoded_path}"
        f"&versionDescriptor.versionType=commit"
        f"&versionDescriptor.version={encoded_commit}"
        "&download=true"
        "&resolveLfs=true"
        "&api-version=7.1"
    )


def _raw_output_path(raw_dir: Path, source_path: str) -> Path:
    relative_path = Path(source_path.lstrip("/"))
    return raw_dir / relative_path


def _fetch_to_raw_and_manifest(
    *,
    ticket_id: str,
    intake: dict[str, Any],
    raw_dir: Path,
    manifest_path: Path,
) -> tuple[dict[str, Any], int, int]:
    project_url = str(intake.get("projectUrl", "")).rstrip("/")
    if not project_url:
        raise RuntimeError("intake.projectUrl is required.")

    cql_paths = [str(path).strip() for path in intake.get("cqlPaths", []) if str(path).strip()]
    if not cql_paths:
        raise RuntimeError("No cqlPaths found in intake artifact.")

    resolved_prs = intake.get("resolvedPullRequests", [])
    if not resolved_prs:
        raise RuntimeError("No resolvedPullRequests found in intake artifact.")

    auth_header = _auth_header_from_env()
    pending_paths = list(cql_paths)
    resolved_rows: list[dict[str, Any]] = []

    for row in resolved_prs:
        pr_id = str(row.get("pullRequestId", "")).strip()
        repository = str(row.get("repositoryId", "") or row.get("repository", "")).strip()
        repository_name = str(row.get("repository", "")).strip()
        source_ref_name = str(row.get("sourceRefName", "")).strip()
        source_commit_id = str(row.get("sourceCommitId", "")).strip()
        if not pr_id or not repository or not source_commit_id:
            continue

        fetched_cql_paths: list[str] = []
        raw_files: list[dict[str, str]] = []

        for cql_path in list(pending_paths):
            item_url = _build_item_url(
                project_url=project_url,
                repository=repository,
                path=cql_path,
                commit_id=source_commit_id,
            )
            try:
                content = _http_get_bytes(item_url, auth_header)
            except Exception:
                continue

            output_path = _raw_output_path(raw_dir, cql_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)

            fetched_cql_paths.append(cql_path)
            raw_files.append(
                {
                    "path": cql_path,
                    "rawFile": output_path.as_posix(),
                }
            )
            pending_paths.remove(cql_path)

        resolved_rows.append(
            {
                "prId": pr_id,
                "repositoryId": str(row.get("repositoryId", "")).strip() or None,
                "repository": repository_name,
                "sourceRefName": source_ref_name,
                "sourceCommitId": source_commit_id,
                "changedCqlPaths": fetched_cql_paths,
                "rawFiles": raw_files,
            }
        )

    payload = {
        "ticketId": ticket_id,
        "method": "mcp-first-with-https-fallback",
        "resolvedPullRequests": resolved_rows,
        "unresolvedCqlPaths": pending_paths,
    }
    _write_json(manifest_path, payload)
    return payload, len(cql_paths) - len(pending_paths), len(pending_paths)


def _parse_cql_text(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    definitions: list[dict[str, Any]] = []
    includes: list[dict[str, Any]] = []
    terminology: list[dict[str, Any]] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        include_match = INCLUDE_RE.match(line)
        if include_match:
            includes.append(
                {
                    "library": include_match.group(1),
                    "version": include_match.group(2) or include_match.group(3),
                    "alias": include_match.group(4),
                    "line": line_number,
                }
            )

        define_match = DEFINE_RE.match(line)
        if define_match:
            definitions.append(
                {
                    "name": define_match.group(1),
                    "line": line_number,
                }
            )

        term_match = TERMINOLOGY_RE.match(line)
        if term_match:
            terminology.append(
                {
                    "kind": term_match.group(1).lower(),
                    "name": term_match.group(2),
                    "identifier": term_match.group(3) or term_match.group(4),
                    "line": line_number,
                }
            )

    return definitions, includes, terminology


def run_fetch_raw_cql(args: argparse.Namespace) -> int:
    ticket_id = _infer_ticket_id(args.ticket_id)
    intake_path = Path(args.intake) if args.intake else Path(f"artifacts/intake/{ticket_id}.json")
    if not intake_path.exists():
        raise FileNotFoundError(f"Missing intake artifact: {intake_path}")

    intake = _load_json(intake_path)
    raw_dir = Path(args.raw_dir) if args.raw_dir else Path(f"artifacts/extraction/raw/{ticket_id}")
    manifest_path = Path(args.out) if args.out else Path(f"artifacts/extraction/{ticket_id}-fetched.json")
    payload, fetched_count, unresolved_count = _fetch_to_raw_and_manifest(
        ticket_id=ticket_id,
        intake=intake,
        raw_dir=raw_dir,
        manifest_path=manifest_path,
    )

    print(f"ticketId={ticket_id}")
    print(f"fetched={fetched_count}")
    print(f"unresolved={unresolved_count}")
    print(f"manifest={manifest_path.as_posix()}")
    return 0 if fetched_count > 0 else 1


def run_download_and_extract(args: argparse.Namespace) -> int:
    ticket_id = _infer_ticket_id(args.ticket_id)
    intake_path = Path(args.intake) if args.intake else Path(f"artifacts/intake/{ticket_id}.json")
    if not intake_path.exists():
        raise FileNotFoundError(f"Missing intake artifact: {intake_path}")

    intake = _load_json(intake_path)
    raw_dir = Path(args.raw_dir) if args.raw_dir else Path(f"artifacts/extraction/raw/{ticket_id}")
    manifest_path = Path(args.out) if args.out else Path(f"artifacts/extraction/{ticket_id}-fetched.json")
    extraction_path = Path(args.extraction_out) if args.extraction_out else Path(f"artifacts/extraction/{ticket_id}.json")

    payload, fetched_count, unresolved_count = _fetch_to_raw_and_manifest(
        ticket_id=ticket_id,
        intake=intake,
        raw_dir=raw_dir,
        manifest_path=manifest_path,
    )

    files: list[dict[str, Any]] = []
    for pr in payload.get("resolvedPullRequests", []):
        pr_id = str(pr.get("prId", "")).strip()
        repository = str(pr.get("repository", "")).strip()
        source_commit_id = str(pr.get("sourceCommitId", "")).strip()
        for raw_file in pr.get("rawFiles", []):
            source_path = str(raw_file.get("path", "")).strip()
            raw_path_rel = str(raw_file.get("rawFile", "")).strip()
            if not source_path or not raw_path_rel:
                continue

            raw_path = Path(raw_path_rel)
            if not raw_path.exists():
                continue

            cql_text = raw_path.read_text(encoding="utf-8-sig")
            definitions, includes, terminology = _parse_cql_text(cql_text)
            files.append(
                {
                    "prId": pr_id,
                    "repository": repository,
                    "path": source_path,
                    "sourceCommitId": source_commit_id,
                    "definitions": definitions,
                    "includes": includes,
                    "terminology": terminology,
                }
            )

    if not files:
        print(f"ticketId={ticket_id}")
        print(f"fetched={fetched_count}")
        print(f"unresolved={unresolved_count}")
        print("extraction=none")
        return 1

    extraction_payload = {
        "ticketId": ticket_id,
        "sourceType": "pr-changed-cql-files",
        "files": files,
        "assumptions": ASSUMPTIONS,
        "status": "extraction-complete",
    }
    _write_json(extraction_path, extraction_payload)

    print(f"ticketId={ticket_id}")
    print(f"fetched={fetched_count}")
    print(f"unresolved={unresolved_count}")
    print(f"manifest={manifest_path.as_posix()}")
    print(f"extraction={extraction_path.as_posix()}")
    print(f"filesParsed={len(files)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extraction-stage non-MCP Azure DevOps fallback helper.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch-raw-cql",
        help="Fetch raw CQL file contents for intake cqlPaths at PR source commit.",
    )
    fetch_parser.add_argument(
        "--ticket-id",
        default="",
        help="Ticket id. If omitted, inferred from state/run-input.json.",
    )
    fetch_parser.add_argument(
        "--intake",
        default="",
        help="Path to intake JSON. Default artifacts/intake/<ticket-id>.json",
    )
    fetch_parser.add_argument(
        "--raw-dir",
        default="",
        help="Optional output directory for raw CQL files. Default artifacts/extraction/raw/<ticket-id>",
    )
    fetch_parser.add_argument(
        "--out",
        default="",
        help="Optional output path for fetched manifest. Default artifacts/extraction/<ticket-id>-fetched.json",
    )
    fetch_parser.set_defaults(func=run_fetch_raw_cql)

    extract_parser = subparsers.add_parser(
        "download-and-extract",
        help="Fetch raw CQL and build extraction artifact from intake cqlPaths at PR source commit.",
    )
    extract_parser.add_argument(
        "--ticket-id",
        default="",
        help="Ticket id. If omitted, inferred from state/run-input.json.",
    )
    extract_parser.add_argument(
        "--intake",
        default="",
        help="Path to intake JSON. Default artifacts/intake/<ticket-id>.json",
    )
    extract_parser.add_argument(
        "--raw-dir",
        default="",
        help="Optional output directory for raw CQL files. Default artifacts/extraction/raw/<ticket-id>",
    )
    extract_parser.add_argument(
        "--out",
        default="",
        help="Optional output path for fetched manifest. Default artifacts/extraction/<ticket-id>-fetched.json",
    )
    extract_parser.add_argument(
        "--extraction-out",
        default="",
        help="Optional output path for extraction JSON. Default artifacts/extraction/<ticket-id>.json",
    )
    extract_parser.set_defaults(func=run_download_and_extract)

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