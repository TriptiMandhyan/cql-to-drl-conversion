#!/usr/bin/env python3
"""Local FastAPI-hosted MCP server for Python helper operations.

This exposes existing repository helper scripts as MCP tools so agents can
invoke them through MCP rather than direct shell commands.
"""

from __future__ import annotations

import base64
import json
import os
import re
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


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


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


def _format_template(value: str, context: dict[str, Any]) -> str:
    """Format a string template while preserving unknown placeholders."""
    return str(value).format_map(_SafeFormatDict({k: str(v) for k, v in context.items()}))


_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env_vars(value: Any) -> Any:
    """Expand ${ENV_VAR} placeholders recursively in strings/dicts/lists."""
    if isinstance(value, str):
        return _ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    return value


def _json_path_get(payload: Any, path: str) -> Any:
    """Read a simple dot-path from a JSON-like payload."""
    current = payload
    for part in str(path or "").split("."):
        key = part.strip()
        if not key:
            continue
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _json_path_set(payload: Any, path: str, value: Any) -> bool:
    """Set a simple dot-path on a JSON-like dict payload."""
    if not isinstance(payload, dict):
        return False

    parts = [part.strip() for part in str(path or "").split(".") if part.strip()]
    if not parts:
        return False

    current: Any = payload
    for key in parts[:-1]:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]

    final_key = parts[-1]
    if not isinstance(current, dict) or final_key not in current:
        return False

    current[final_key] = value
    return True


def _http_json_request(
    *,
    url: str,
    method: str,
    headers: dict[str, str] | None,
    body: Any,
    timeout_seconds: int,
) -> Any:
    """Execute an HTTP request and parse the JSON response."""
    request_data: bytes | None = None
    if body is not None:
        request_data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, data=request_data, method=str(method or "GET").upper())
    
    # Set Content-Length explicitly for POST with no body to match Postman behavior
    if request_data is None and method.upper() == "POST":
        req.add_header("Content-Length", "0")
    
    for key, val in (headers or {}).items():
        req.add_header(str(key), str(val))

    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8")

    if not raw.strip():
        raise ValueError(f"Empty response body from {url}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Non-JSON response from {url}: {exc}") from exc


def _normalize_auth_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    """Normalize outgoing auth headers to avoid malformed Authorization values."""
    normalized: dict[str, str] = {
        str(k): str(v) for k, v in (headers or {}).items()
    }

    auth_value = normalized.get("Authorization")
    if auth_value:
        trimmed = str(auth_value).strip()
        lower = trimmed.lower()
        if lower.startswith("basic basic "):
            normalized["Authorization"] = "Basic " + trimmed[12:].strip()

    return normalized


def _redacted_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    """Return a copy of headers with sensitive values redacted."""
    out = {str(k): str(v) for k, v in (headers or {}).items()}
    for key in list(out.keys()):
        if key.lower() in {"authorization", "x-api-key", "api-key"}:
            original = str(out[key])
            # Always show length and first/last 4 chars for debugging without exposing full value
            if len(original) > 8:
                out[key] = f"<redacted len={len(original)} start={original[:4]}... end=...{original[-4:]}>"
            elif len(original) > 0:
                out[key] = f"<redacted len={len(original)}>"
            else:
                out[key] = "<redacted len=0 EMPTY>"
    return out


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
def fetch_measure_json_via_api_config(
    ticket_id: str = "",
    measure_slug: str = "",
    measure_specification: str = "",
) -> dict[str, Any]:
    """Fetch and persist measure JSON using configured auth+data API endpoints.

    Args:
        ticket_id: Optional ticket id. If omitted, helper infers from state/run-input.json.
        measure_slug: Optional explicit measure slug (e.g., mips007rate1).
        measure_specification: Optional explicit measureSpecification value.
    """
    try:
        resolved_ticket = _resolve_ticket_id(ticket_id)

        config_path = ROOT_DIR / ".github" / "orchestration" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        api_payload = config.get("apiPayload") or {}
        if not api_payload.get("enabled", False):
            return {
                "ok": False,
                "returnCode": 1,
                "error": "apiPayload.enabled must be true",
            }

        intake_path = ROOT_DIR / "artifacts" / "intake" / f"{resolved_ticket}.json"
        intake = json.loads(intake_path.read_text(encoding="utf-8-sig")) if intake_path.exists() else {}

        cql_paths = intake.get("cqlPaths") or []
        first_cql = str(cql_paths[0]) if cql_paths else ""

        derived_year = ""
        year_match = re.search(r"/(20\d{2})/", first_cql)
        if year_match:
            derived_year = year_match.group(1)

        family_default = str((config.get("measureFamilies") or {}).get("default") or "mips").strip().lower()

        slug = str(measure_slug).strip().lower()
        if not slug and first_cql:
            stem = Path(first_cql).stem.strip().lower()
            numeric_prefix_match = re.match(r"^(\d+)(.*)$", stem)
            if numeric_prefix_match:
                number = numeric_prefix_match.group(1).zfill(3)
                suffix = numeric_prefix_match.group(2)
                slug = f"{family_default}{number}{suffix}"
            else:
                slug = stem

        if not slug:
            return {
                "ok": False,
                "returnCode": 1,
                "error": "Unable to resolve measure_slug; provide measure_slug explicitly",
            }

        number_match = re.search(r"(\d{1,4})", slug)
        rate_match = re.search(r"rate(\d+)", slug)

        context = {
            "ticketId": resolved_ticket,
            "measureSlug": slug,
            "measureFamilyLower": family_default,
            "measureYear": derived_year,
            "measureYearShort": derived_year[-2:] if len(derived_year) >= 2 else "",
            "measureNumber": number_match.group(1) if number_match else "",
            "measureNumberPadded": number_match.group(1).zfill(3) if number_match else "",
            "rateNumber": rate_match.group(1) if rate_match else "",
        }

        data_cfg = api_payload.get("data") or {}
        specification = str(measure_specification).strip()
        if not specification:
            specification_template = str(data_cfg.get("measureSpecificationFormat") or "{measureSlug}")
            specification = _format_template(specification_template, context)
        else:
            # Keep external spec prefix/version but enforce slug parity with DRL/CQL/JSON naming.
            spec_parts = str(specification).split("-")
            if len(spec_parts) >= 3:
                spec_parts[-1] = slug
                specification = "-".join(spec_parts)

        context["measureSpecification"] = specification

        auth_cfg = api_payload.get("auth") or {}
        auth_url = str(auth_cfg.get("url") or "").strip()
        if not auth_url:
            return {"ok": False, "returnCode": 1, "error": "apiPayload.auth.url is required"}

        # Check required env vars before expansion
        required_env = auth_cfg.get("requiredEnv") or []
        missing_env = [var for var in required_env if not os.environ.get(var)]
        if missing_env:
            return {
                "ok": False,
                "returnCode": 1,
                "phase": "auth-config",
                "error": f"Required environment variables not set: {', '.join(missing_env)}",
                "missingVars": missing_env,
            }

        auth_method = str(auth_cfg.get("method") or "POST").upper()
        auth_headers = _normalize_auth_headers(_expand_env_vars(auth_cfg.get("headers") or {}))
        auth_body_template = auth_cfg.get("bodyTemplate")
        auth_body = _expand_env_vars(auth_body_template) if auth_body_template is not None else None

        unresolved_auth_headers = {
            k: v for k, v in auth_headers.items() if "${" in str(v)
        }
        if unresolved_auth_headers:
            return {
                "ok": False,
                "returnCode": 1,
                "phase": "auth-config",
                "error": "Unresolved auth header placeholders detected",
                "requestHeaders": _redacted_headers(unresolved_auth_headers),
            }

        if isinstance(auth_body, dict):
            unresolved_auth_body = {
                k: v for k, v in auth_body.items() if "${" in str(v)
            }
            if unresolved_auth_body:
                return {
                    "ok": False,
                    "returnCode": 1,
                    "phase": "auth-config",
                    "error": "Unresolved auth body placeholders detected",
                    "requestBody": unresolved_auth_body,
                }

        try:
            auth_response = _http_json_request(
                url=auth_url,
                method=auth_method,
                headers=auth_headers,
                body=auth_body,
                timeout_seconds=120,
            )
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            
            # Add diagnostic info about Authorization header
            auth_header_diagnostics = {}
            auth_value = auth_headers.get("Authorization", "")
            if auth_value:
                auth_header_diagnostics["authHeaderLength"] = len(auth_value)
                if len(auth_value) > 8:
                    auth_header_diagnostics["authHeaderPreview"] = f"{auth_value[:4]}...{auth_value[-4:]}"
                elif len(auth_value) > 0:
                    auth_header_diagnostics["authHeaderPreview"] = f"<length {len(auth_value)}>"
                else:
                    auth_header_diagnostics["authHeaderPreview"] = "<EMPTY>"
            
            return {
                "ok": False,
                "returnCode": 1,
                "phase": "auth",
                "error": f"HTTP {e.code}: {e.reason}",
                "url": auth_url,
                "requestHeaders": _redacted_headers(auth_headers),
                "authDiagnostics": auth_header_diagnostics,
                "responseBody": body[:2000],
            }

        auth_from_response = data_cfg.get("authorizationFromAuthResponse") or {}
        token_json_path = str(
            auth_from_response.get("tokenJsonPath")
            or auth_cfg.get("tokenJsonPath")
            or "access_token"
        )
        token = _json_path_get(auth_response, token_json_path)
        auth_response_sanitized = auth_response
        try:
            auth_response_sanitized = json.loads(json.dumps(auth_response))
        except Exception:
            pass

        if isinstance(auth_response_sanitized, dict):
            _json_path_set(auth_response_sanitized, token_json_path, "<redacted>")

        if not token:
            return {
                "ok": False,
                "returnCode": 1,
                "error": f"Auth response did not include token at configured tokenJsonPath: {token_json_path}",
                "authResponse": auth_response_sanitized,
            }

        data_url_template = str(data_cfg.get("urlTemplate") or "").strip()
        if not data_url_template:
            return {"ok": False, "returnCode": 1, "error": "apiPayload.data.urlTemplate is required"}

        data_url = _format_template(data_url_template, context)
        data_method = str(data_cfg.get("method") or "GET").upper()
        data_headers = _normalize_auth_headers(_expand_env_vars(data_cfg.get("headers") or {}))

        auth_header_name = str(auth_from_response.get("headerName") or "Authorization")
        auth_header_template = str(auth_from_response.get("headerValueTemplate") or "Bearer {token}")
        data_headers[auth_header_name] = _format_template(auth_header_template, {"token": token})

        data_body_template = data_cfg.get("bodyTemplate")
        data_body = None
        if data_body_template is not None:
            expanded_body = _expand_env_vars(data_body_template)
            if isinstance(expanded_body, str):
                data_body = _format_template(expanded_body, context)
            elif isinstance(expanded_body, dict):
                data_body = {
                    k: _format_template(v, context) if isinstance(v, str) else v
                    for k, v in expanded_body.items()
                }
            else:
                data_body = expanded_body

        try:
            payload = _http_json_request(
                url=data_url,
                method=data_method,
                headers=data_headers,
                body=data_body,
                timeout_seconds=120,
            )
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            return {
                "ok": False,
                "returnCode": 1,
                "phase": "data",
                "error": f"HTTP {e.code}: {e.reason}",
                "url": data_url,
                "measureSpecification": specification,
                "authResponse": auth_response_sanitized,
                "responseBody": body[:2000],
            }

        if payload in ({}, [], None):
            return {
                "ok": False,
                "returnCode": 1,
                "error": "Data API returned an empty JSON payload",
            }

        output_pattern = str(data_cfg.get("outputFilePattern") or "{measureSlug}.json")
        output_name = _format_template(output_pattern, context)
        output_dir = ROOT_DIR / "artifacts" / "pr-assets" / resolved_ticket
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / output_name
        output_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "returnCode": 0,
            "ticketId": resolved_ticket,
            "measureSlug": slug,
            "measureSpecification": specification,
            "authResponse": auth_response_sanitized,
            "outputPath": str(output_file.relative_to(ROOT_DIR)).replace("\\", "/"),
            "bytes": output_file.stat().st_size,
        }
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return {
            "ok": False,
            "returnCode": 1,
            "error": f"HTTP {e.code}: {e.reason}",
            "responseBody": body[:2000],
        }
    except Exception as e:
        return {
            "ok": False,
            "returnCode": 1,
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
    # Be tolerant to SDK/client path expectations:
    # - Some variants expose MCP transport at subapp root.
    # - Others expose it under /mcp inside the subapp.
    # Mount both prefixes so clients configured for /mcp do not get 404.
    app.mount("/mcp", _mcp_asgi_app)
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