#!/usr/bin/env python3
"""Local FastAPI-hosted MCP server for Python helper operations.

This exposes existing repository helper scripts as MCP tools so agents can
invoke them through MCP rather than direct shell commands.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from state_manager import PipelineStage, TicketStateManager
from learning_engine import LearningEngine


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_HOST = os.environ.get("LOCAL_MCP_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("LOCAL_MCP_PORT", "8765"))

mcp = FastMCP("local-python-tools")
# Create the streamable app once to initialize session manager lazily.
_mcp_asgi_app = mcp.streamable_http_app()


def _run_python_script(args: list[str]) -> dict[str, Any]:
    """Run a repository helper script and return command result payload."""
    command = [sys.executable, *args]
    proc = subprocess.run(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returnCode": proc.returncode,
        "command": " ".join(command),
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _resolve_ticket_id(ticket_id: str = "") -> str:
    """Resolve ticket ID from argument or run-input context."""
    ticket = ticket_id.strip()
    return ticket if ticket else TicketStateManager.get_current_ticket_id()


def _safe_remove_path(path: Path) -> bool:
    """Remove a file or directory if it exists."""
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def _derive_drl_candidates(ticket_id: str) -> list[Path]:
    """Build DRL candidate paths from extraction and intake traceability data."""
    candidates: set[Path] = set()

    source_paths: set[str] = set()

    extraction_file = ROOT_DIR / "artifacts" / "extraction" / f"{ticket_id}.json"
    if extraction_file.exists():
        try:
            extraction_payload = json.loads(extraction_file.read_text(encoding="utf-8-sig"))
            for file_entry in extraction_payload.get("files", []):
                source_path = str((file_entry or {}).get("path") or "").strip()
                if source_path:
                    source_paths.add(source_path)
        except Exception:
            pass

    intake_file = ROOT_DIR / "artifacts" / "intake" / f"{ticket_id}.json"
    if intake_file.exists():
        try:
            intake_payload = json.loads(intake_file.read_text(encoding="utf-8-sig"))
            for cql_path in intake_payload.get("cqlPaths", []):
                source_path = str(cql_path or "").strip()
                if source_path:
                    source_paths.add(source_path)
        except Exception:
            pass

    raw_ticket_dir = ROOT_DIR / "artifacts" / "extraction" / "raw" / ticket_id
    if raw_ticket_dir.exists() and raw_ticket_dir.is_dir():
        for cql_file in raw_ticket_dir.rglob("*.cql"):
            source_paths.add(str(cql_file))

    for source_path in source_paths:
        stem = Path(source_path).stem
        if not stem:
            continue
        lower = stem.lower()
        candidates.add(ROOT_DIR / "artifacts" / "conversion" / f"{stem}.drl")
        candidates.add(ROOT_DIR / "artifacts" / "conversion" / f"mips{stem}.drl")
        candidates.add(ROOT_DIR / "artifacts" / "conversion" / f"mips{lower}.drl")

    return sorted(candidates)


@mcp.tool()
def enrich_intake(ticket_id: str = "") -> dict[str, Any]:
    """Enrich intake cqlPaths from latest PR iteration changed files.

    Args:
        ticket_id: Optional ticket id. If omitted, helper infers from state/run-input.json.
    """
    args = ["scripts/ado_fallback.py", "enrich-intake"]
    if ticket_id.strip():
        args.extend(["--ticket-id", ticket_id.strip()])
    return _run_python_script(args)


@mcp.tool()
def fetch_raw_cql(ticket_id: str = "") -> dict[str, Any]:
    """Fetch raw CQL files from PR source commit for intake cqlPaths.

    Args:
        ticket_id: Optional ticket id. If omitted, helper infers from state/run-input.json.
    """
    args = ["scripts/ado_extraction_fallback.py", "fetch-raw-cql"]
    if ticket_id.strip():
        args.extend(["--ticket-id", ticket_id.strip()])
    return _run_python_script(args)


@mcp.tool()
def validate_conversion_artifacts(ticket_id: str) -> dict[str, Any]:
    """Run conversion artifact validation for a ticket.

    Args:
        ticket_id: Required ticket id for validation target.
    """
    ticket = ticket_id.strip()
    if not ticket:
        return {
            "ok": False,
            "returnCode": 2,
            "command": "",
            "stdout": "",
            "stderr": "ticket_id is required",
        }

    return _run_python_script(
        ["scripts/validate_conversion_artifacts.py", "--ticket", ticket]
    )


@mcp.tool()
def get_pr_changes(
    project_url: str,
    repository: str,
    pull_request_id: str,
) -> dict[str, Any]:
    """Fetch changed files from a pull request's latest iteration.

    Args:
        project_url: Azure DevOps project URL (e.g., https://dev.azure.com/org/project)
        repository: Repository name or ID
        pull_request_id: Pull request ID number

    Returns:
        Dict with ok, returnCode, and either cqlPaths (list) or error message
    """
    try:
        pat = os.environ.get("ADO_PAT", "").strip()
        if not pat:
            return {
                "ok": False,
                "returnCode": 1,
                "cqlPaths": [],
                "error": "ADO_PAT environment variable is required",
            }

        token = base64.b64encode(f":{pat}".encode("ascii")).decode("ascii")
        auth_header = f"Basic {token}"

        project_url = str(project_url).rstrip("/")
        repository = str(repository).strip()
        pr_id = str(pull_request_id).strip()

        # Fetch PR iterations
        iterations_url = (
            f"{project_url}/_apis/git/repositories/{repository}/pullRequests/{pr_id}/iterations"
            "?api-version=7.1"
        )
        
        req = urllib.request.Request(iterations_url)
        req.add_header("Authorization", auth_header)
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=120) as resp:
            iterations_payload = json.loads(resp.read().decode("utf-8"))

        iterations = iterations_payload.get("value", [])
        if not iterations:
            return {
                "ok": True,
                "returnCode": 0,
                "cqlPaths": [],
                "message": "No iterations found in PR",
            }

        latest_iteration_id = max(int(it.get("id", 0)) for it in iterations)

        # Fetch changes for latest iteration
        changes_url = (
            f"{project_url}/_apis/git/repositories/{repository}/pullRequests/{pr_id}/"
            f"iterations/{latest_iteration_id}/changes?$top=2000&api-version=7.1"
        )
        
        req = urllib.request.Request(changes_url)
        req.add_header("Authorization", auth_header)
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=120) as resp:
            changes_payload = json.loads(resp.read().decode("utf-8"))

        cql_paths = sorted(
            {
                str((entry.get("item") or {}).get("path") or "").strip()
                for entry in changes_payload.get("changeEntries", [])
                if str((entry.get("item") or {}).get("path") or "").lower().endswith(".cql")
            }
        )

        return {
            "ok": True,
            "returnCode": 0,
            "cqlPaths": cql_paths,
            "iterationId": latest_iteration_id,
            "changeCount": len(changes_payload.get("changeEntries", [])),
        }

    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "returnCode": 1,
            "cqlPaths": [],
            "error": f"HTTP {e.code}: {e.reason}",
        }
    except Exception as e:
        return {
            "ok": False,
            "returnCode": 1,
            "cqlPaths": [],
            "error": str(e),
        }


@mcp.tool()
def state_list_pipeline_stages() -> dict[str, Any]:
    """List canonical pipeline stage values."""
    return {
        "ok": True,
        "stages": [stage.value for stage in PipelineStage],
    }


@mcp.tool()
def state_get_current_ticket() -> dict[str, Any]:
    """Resolve current ticket ID from state/run-input.json."""
    try:
        return {
            "ok": True,
            "ticketId": TicketStateManager.get_current_ticket_id(),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


@mcp.tool()
def state_read_pipeline(ticket_id: str = "") -> dict[str, Any]:
    """Read pipeline status for a ticket (or current ticket when omitted)."""
    try:
        resolved_ticket = _resolve_ticket_id(ticket_id)
        return {
            "ok": True,
            "ticketId": resolved_ticket,
            "pipeline": TicketStateManager.read_pipeline_status(resolved_ticket),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


@mcp.tool()
def state_read_approval(ticket_id: str = "") -> dict[str, Any]:
    """Read approval status for a ticket (or current ticket when omitted)."""
    try:
        resolved_ticket = _resolve_ticket_id(ticket_id)
        return {
            "ok": True,
            "ticketId": resolved_ticket,
            "approval": TicketStateManager.read_approval_status(resolved_ticket),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


@mcp.tool()
def state_write_pipeline(stage: str, details: str = "", ticket_id: str = "") -> dict[str, Any]:
    """Write pipeline status using canonical stage validation."""
    try:
        resolved_ticket = _resolve_ticket_id(ticket_id)
        path = TicketStateManager.write_pipeline_status(resolved_ticket, stage, details)
        return {
            "ok": True,
            "ticketId": resolved_ticket,
            "stage": stage,
            "path": str(path),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


@mcp.tool()
def state_write_approval(
    approved: bool,
    approved_by: str = "",
    notes: str = "",
    ticket_id: str = "",
) -> dict[str, Any]:
    """Write approval status for a ticket (or current ticket when omitted)."""
    try:
        resolved_ticket = _resolve_ticket_id(ticket_id)
        normalized_approver = approved_by.strip() or None
        path = TicketStateManager.write_approval_status(
            resolved_ticket,
            bool(approved),
            normalized_approver,
            notes,
        )
        return {
            "ok": True,
            "ticketId": resolved_ticket,
            "approved": bool(approved),
            "path": str(path),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


@mcp.tool()
def state_reset_ticket_baseline(
    ticket_id: str = "",
    clear_legacy_singleton_state: bool = False,
) -> dict[str, Any]:
    """Reset a ticket to first-time baseline.

    This removes ticket-specific artifacts and per-ticket state so the ticket
    appears as if it has never run in the local workflow.

    Args:
        ticket_id: Optional ticket id. If omitted, resolves from state/run-input.json.
        clear_legacy_singleton_state: If true, removes legacy singleton state files
            when they belong to the same ticket.
    """
    try:
        resolved_ticket = _resolve_ticket_id(ticket_id)

        deleted: list[str] = []
        skipped: list[str] = []

        # Deterministic artifact cleanup for this ticket.
        targets = [
            ROOT_DIR / "artifacts" / "intake" / f"{resolved_ticket}.json",
            ROOT_DIR / "artifacts" / "extraction" / f"{resolved_ticket}.json",
            ROOT_DIR / "artifacts" / "extraction" / f"{resolved_ticket}-fetched.json",
            ROOT_DIR / "artifacts" / "extraction" / "raw" / resolved_ticket,
            ROOT_DIR / "artifacts" / "plan" / f"{resolved_ticket}.md",
            ROOT_DIR / "artifacts" / "pr" / f"{resolved_ticket}-pr.md",
            ROOT_DIR / "artifacts" / "conversion" / f"{resolved_ticket}-mapping.md",
            ROOT_DIR / "artifacts" / "conversion" / f"{resolved_ticket}.drl",
        ]
        targets.extend(_derive_drl_candidates(resolved_ticket))

        for path in sorted(set(targets)):
            if _safe_remove_path(path):
                deleted.append(str(path.relative_to(ROOT_DIR)).replace("\\", "/"))
            else:
                skipped.append(str(path.relative_to(ROOT_DIR)).replace("\\", "/"))

        # Remove ticket state directory entirely.
        ticket_state_dir = ROOT_DIR / "state" / "tickets" / resolved_ticket
        if _safe_remove_path(ticket_state_dir):
            deleted.append(str(ticket_state_dir.relative_to(ROOT_DIR)).replace("\\", "/"))
        else:
            skipped.append(str(ticket_state_dir.relative_to(ROOT_DIR)).replace("\\", "/"))

        # Normalize and update index.
        tickets_dir = ROOT_DIR / "state" / "tickets"
        tickets_dir.mkdir(parents=True, exist_ok=True)

        index_path = tickets_dir / "index.json"
        if index_path.exists() and index_path.is_dir():
            return {
                "ok": False,
                "ticketId": resolved_ticket,
                "error": "state/tickets/index.json is a directory; replace with a JSON file",
                "deleted": deleted,
                "skipped": skipped,
            }

        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8-sig"))
        else:
            index = {
                "currentTicketId": None,
                "lastUpdated": "",
                "tickets": {},
            }

        tickets_map = index.get("tickets") or {}
        if isinstance(tickets_map, dict):
            tickets_map.pop(resolved_ticket, None)
        else:
            tickets_map = {}
        index["tickets"] = tickets_map

        if index.get("currentTicketId") == resolved_ticket:
            index["currentTicketId"] = None

        index["lastUpdated"] = datetime.now().isoformat()
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

        if clear_legacy_singleton_state:
            for singleton in [
                ROOT_DIR / "state" / "pipeline-status.json",
                ROOT_DIR / "state" / "approval-status.json",
            ]:
                if not singleton.exists() or singleton.is_dir():
                    continue
                try:
                    content = json.loads(singleton.read_text(encoding="utf-8-sig"))
                except Exception:
                    continue
                if str(content.get("ticketId") or "") == resolved_ticket:
                    _safe_remove_path(singleton)
                    deleted.append(str(singleton.relative_to(ROOT_DIR)).replace("\\", "/"))

        return {
            "ok": True,
            "ticketId": resolved_ticket,
            "deleted": sorted(set(deleted)),
            "skipped": sorted(set(skipped)),
            "indexPath": "state/tickets/index.json",
            "baselineState": "no ticket-scoped state",
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


# ============================================================================
# Learning Engine Tools (Passive, Non-Blocking)
# ============================================================================


@mcp.tool()
def learning_record_execution(
    ticket_id: str,
    stage: str,
    elapsed_seconds: float,
    success: bool,
    details: str = "",
) -> dict[str, Any]:
    """Record execution metrics for a pipeline stage (non-blocking).

    Args:
        ticket_id: Ticket being processed
        stage: Pipeline stage (intake, extraction, approval, conversion, pr)
        elapsed_seconds: Time taken for stage
        success: Whether stage succeeded
        details: Optional context info

    Returns:
        Dict with ok status (always returns ok=true for non-blocking)
    """
    try:
        LearningEngine.record_execution(ticket_id, stage, elapsed_seconds, success, details)
        return {"ok": True, "recorded": True}
    except Exception as e:
        # Silent fail: never propagate errors
        return {"ok": True, "recorded": False, "reason": str(e)}


@mcp.tool()
def learning_record_cql_patterns(ticket_id: str, cql_content: str) -> dict[str, Any]:
    """Analyze CQL and record patterns (non-blocking).

    Args:
        ticket_id: Ticket being processed
        cql_content: CQL text to analyze

    Returns:
        Dict with ok status (always returns ok=true for non-blocking)
    """
    try:
        LearningEngine.record_cql_patterns(ticket_id, cql_content)
        return {"ok": True, "recorded": True}
    except Exception as e:
        # Silent fail: never propagate errors
        return {"ok": True, "recorded": False, "reason": str(e)}


@mcp.tool()
def learning_record_error(
    ticket_id: str,
    stage: str,
    error_type: str,
    error_message: str,
) -> dict[str, Any]:
    """Record error pattern for troubleshooting (non-blocking).

    Args:
        ticket_id: Ticket where error occurred
        stage: Pipeline stage where error occurred
        error_type: Error category (validation, mcp-call, parsing, etc.)
        error_message: Error description

    Returns:
        Dict with ok status (always returns ok=true for non-blocking)
    """
    try:
        LearningEngine.record_error(ticket_id, stage, error_type, error_message)
        return {"ok": True, "recorded": True}
    except Exception as e:
        # Silent fail: never propagate errors
        return {"ok": True, "recorded": False, "reason": str(e)}


@mcp.tool()
def learning_get_summary() -> dict[str, Any]:
    """Get current learning summary (aggregated metrics/patterns/errors).

    Returns:
        Dict with metrics, patterns, errors summary
    """
    try:
        return {"ok": True, "summary": LearningEngine.get_summary()}
    except Exception as e:
        # Silent fail: return empty summary
        return {"ok": False, "error": str(e)}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # FastAPI-mounted subapps do not automatically drive the child lifespan.
    # Run the MCP session manager explicitly so tool requests can be handled.
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Local Python MCP Server", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if hasattr(mcp, "streamable_http_app"):
    # streamable_http_app already serves on /mcp, so mount at root.
    app.mount("/", _mcp_asgi_app)
elif hasattr(mcp, "sse_app"):
    # Compatibility fallback for older SDK variants.
    # sse_app exposes its own route set (for example /sse, /messages).
    app.mount("/", mcp.sse_app())
else:
    raise RuntimeError("Installed MCP Python SDK does not expose an HTTP app transport.")


def main() -> int:
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())