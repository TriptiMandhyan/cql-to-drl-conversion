"""
State Manager for Multi-Ticket Workflow

Handles ticket-scoped state management, replacing singleton state files with
per-ticket directories while maintaining a master index for all tickets.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Union
import shutil


class PipelineStage(str, Enum):
    """Canonical pipeline stages for all agents."""

    INTAKE_START = "intake-start"
    INTAKE_COMPLETE = "intake-complete"
    EXTRACTION_COMPLETE = "extraction-complete"
    AWAITING_APPROVAL = "awaiting-approval"
    CONVERSION_READY = "conversion-ready"
    CONVERSION_COMPLETE = "conversion-complete"
    PR_READY = "pr-ready"
    PR_SUBMITTED = "pr-submitted"


class TicketStateManager:
    """Manages state for individual tickets with per-ticket directories."""
    
    STATE_DIR = Path("state")
    TICKETS_DIR = STATE_DIR / "tickets"
    INDEX_FILE = TICKETS_DIR / "index.json"
    RUN_INPUT_FILE = STATE_DIR / "run-input.json"
    
    @classmethod
    def _ensure_dir(cls, path: Path) -> None:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _get_ticket_dir(cls, ticket_id: str) -> Path:
        """Get the directory path for a ticket."""
        return cls.TICKETS_DIR / ticket_id
    
    @classmethod
    def get_current_ticket_id(cls) -> str:
        """Read current ticket ID from run-input.json.
        
        Returns:
            Ticket ID (e.g., '1024415')
            
        Raises:
            RuntimeError: If run-input.json doesn't exist or has no ticketId
        """
        if not cls.RUN_INPUT_FILE.exists():
            raise RuntimeError(f"Missing {cls.RUN_INPUT_FILE}")
        
        data = json.loads(cls.RUN_INPUT_FILE.read_text(encoding="utf-8-sig"))
        
        # Try ticketId first (new format), fallback to ticketUrl parsing
        ticket_id = data.get("ticketId")
        if ticket_id:
            return str(ticket_id)
        
        ticket_url = data.get("ticketUrl", "")
        if not ticket_url:
            raise RuntimeError("No ticketId or ticketUrl in run-input.json")
        
        # Extract ID from URL like .../edit/1024415 or .../edit/1024415/
        try:
            parts = [p for p in ticket_url.split("/") if p]  # Filter out empty parts from trailing slash
            return str(int(parts[-1]))
        except (IndexError, ValueError):
            raise RuntimeError(f"Could not parse ticket ID from URL: {ticket_url}")
    
    @classmethod
    def read_ticket_state(cls, ticket_id: str, filename: str) -> Dict[str, Any]:
        """Read state file for a ticket.
        
        Args:
            ticket_id: The ticket ID
            filename: Name of state file (e.g., 'pipeline-status.json')
            
        Returns:
            Parsed JSON content
            
        Raises:
            FileNotFoundError: If state file doesn't exist for this ticket
        """
        path = cls._get_ticket_dir(ticket_id) / filename
        if not path.exists():
            raise FileNotFoundError(f"No {filename} for ticket {ticket_id}")
        return json.loads(path.read_text(encoding="utf-8-sig"))
    
    @classmethod
    def write_ticket_state(cls, ticket_id: str, filename: str, data: Dict[str, Any]) -> Path:
        """Write state file for a ticket atomically.
        
        Args:
            ticket_id: The ticket ID
            filename: Name of state file
            data: Data to write
            
        Returns:
            Path where file was written
        """
        ticket_dir = cls._get_ticket_dir(ticket_id)
        cls._ensure_dir(ticket_dir)
        
        path = ticket_dir / filename
        
        # Atomic write: write to temp, then rename
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(data, indent=2))
        temp_path.replace(path)
        
        return path
    
    @classmethod
    def read_pipeline_status(cls, ticket_id: str) -> Dict[str, Any]:
        """Read pipeline status for a ticket."""
        return cls.read_ticket_state(ticket_id, "pipeline-status.json")
    
    @classmethod
    def _normalize_stage(cls, stage: Union[str, PipelineStage]) -> str:
        """Normalize and validate stage against canonical pipeline values."""
        value = stage.value if isinstance(stage, PipelineStage) else str(stage)
        allowed = {item.value for item in PipelineStage}
        if value not in allowed:
            raise ValueError(
                f"Invalid pipeline stage '{value}'. Allowed values: {sorted(allowed)}"
            )
        return value

    @classmethod
    def write_pipeline_status(
        cls,
        ticket_id: str,
        stage: Union[str, PipelineStage],
        details: str = "",
    ) -> Path:
        """Write pipeline status for a ticket.
        
        Args:
            ticket_id: The ticket ID
            stage: New stage (e.g., 'intake-complete', 'awaiting-approval')
            details: Optional stage details
            
        Returns:
            Path where file was written
        """
        normalized_stage = cls._normalize_stage(stage)
        data = {
            "ticketId": ticket_id,
            "stage": normalized_stage,
            "updatedAt": datetime.now().isoformat(),
            "details": details
        }
        result = cls.write_ticket_state(ticket_id, "pipeline-status.json", data)
        cls._update_index(ticket_id, stage=normalized_stage)
        cls._add_history_entry(ticket_id, normalized_stage, "system")
        return result
    
    @classmethod
    def read_approval_status(cls, ticket_id: str) -> Dict[str, Any]:
        """Read approval status for a ticket."""
        return cls.read_ticket_state(ticket_id, "approval-status.json")
    
    @classmethod
    def write_approval_status(cls, ticket_id: str, approved: bool, 
                             approved_by: Optional[str] = None, 
                             notes: str = "") -> Path:
        """Write approval status for a ticket.
        
        Args:
            ticket_id: The ticket ID
            approved: Approval status
            approved_by: Name of approver (if approved)
            notes: Optional approval notes
            
        Returns:
            Path where file was written
        """
        data = {
            "ticketId": ticket_id,
            "approved": approved,
            "approvedBy": approved_by,
            "approvedAt": datetime.now().isoformat() if approved else None,
            "notes": notes
        }
        result = cls.write_ticket_state(ticket_id, "approval-status.json", data)
        cls._update_index(ticket_id, approved=approved)
        return result
    
    @classmethod
    def _ensure_index_exists(cls) -> None:
        """Ensure master index file exists."""
        if cls.INDEX_FILE.exists():
            return
        
        cls._ensure_dir(cls.TICKETS_DIR)
        default_index = {
            "currentTicketId": None,
            "lastUpdated": datetime.now().isoformat(),
            "tickets": {}
        }
        cls.INDEX_FILE.write_text(json.dumps(default_index, indent=2))
    
    @classmethod
    def _update_index(cls, ticket_id: str, stage: Optional[str] = None, 
                     approved: Optional[bool] = None) -> None:
        """Update master index with ticket info."""
        cls._ensure_index_exists()
        
        index = json.loads(cls.INDEX_FILE.read_text(encoding="utf-8-sig"))
        
        if ticket_id not in index["tickets"]:
            index["tickets"][ticket_id] = {
                "stage": PipelineStage.INTAKE_START.value,
                "approved": False,
                "ingestedAt": datetime.now().isoformat()
            }
        
        if stage:
            index["tickets"][ticket_id]["stage"] = stage
        if approved is not None:
            index["tickets"][ticket_id]["approved"] = approved
        
        index["currentTicketId"] = ticket_id
        index["lastUpdated"] = datetime.now().isoformat()
        
        cls.INDEX_FILE.write_text(json.dumps(index, indent=2))
    
    @classmethod
    def _add_history_entry(cls, ticket_id: str, stage: str, actor: str) -> None:
        """Add entry to ticket's history log."""
        ticket_dir = cls._get_ticket_dir(ticket_id)
        cls._ensure_dir(ticket_dir)
        
        history_file = ticket_dir / "history.json"
        
        if history_file.exists():
            history = json.loads(history_file.read_text(encoding="utf-8-sig"))
        else:
            history = {"ticketId": ticket_id, "transitions": []}
        
        history["transitions"].append({
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
            "actor": actor
        })
        
        history_file.write_text(json.dumps(history, indent=2))
    
    @classmethod
    def get_all_tickets(cls) -> Dict[str, Dict[str, Any]]:
        """Get index of all tickets and their states."""
        cls._ensure_index_exists()
        index = json.loads(cls.INDEX_FILE.read_text(encoding="utf-8-sig"))
        return index["tickets"]
    
    @classmethod
    def migrate_singleton_files(cls) -> None:
        """Migrate from old singleton state files to per-ticket structure.
        
        Reads legacy files:
        - state/pipeline-status.json
        - state/approval-status.json
        
        Creates per-ticket structure with history.
        """
        old_pipeline = cls.STATE_DIR / "pipeline-status.json"
        old_approval = cls.STATE_DIR / "approval-status.json"
        
        if old_pipeline.exists():
            pipeline_data = json.loads(old_pipeline.read_text(encoding="utf-8-sig"))
            ticket_id = pipeline_data.get("ticketId")
            
            if ticket_id:
                print(f"Migrating pipeline state for ticket {ticket_id}")
                cls.write_ticket_state(ticket_id, "pipeline-status.json", pipeline_data)
                cls._add_history_entry(ticket_id, pipeline_data.get("stage"), "migration")
        
        if old_approval.exists():
            approval_data = json.loads(old_approval.read_text(encoding="utf-8-sig"))
            ticket_id = approval_data.get("ticketId")
            
            if ticket_id:
                print(f"Migrating approval state for ticket {ticket_id}")
                cls.write_ticket_state(ticket_id, "approval-status.json", approval_data)
        
        print("Migration complete")


# Convenience functions for scripts
def get_ticket_id() -> str:
    """Get current ticket ID from run-input.json."""
    return TicketStateManager.get_current_ticket_id()


def read_pipeline(ticket_id: str) -> Dict[str, Any]:
    """Read pipeline status for ticket."""
    return TicketStateManager.read_pipeline_status(ticket_id)


def write_pipeline(ticket_id: str, stage: Union[str, PipelineStage], details: str = "") -> Path:
    """Write pipeline status for ticket."""
    return TicketStateManager.write_pipeline_status(ticket_id, stage, details)


def list_pipeline_stages() -> list[str]:
    """List canonical pipeline status values."""
    return [item.value for item in PipelineStage]


def read_approval(ticket_id: str) -> Dict[str, Any]:
    """Read approval status for ticket."""
    return TicketStateManager.read_approval_status(ticket_id)


def write_approval(ticket_id: str, approved: bool, approved_by: Optional[str] = None, 
                  notes: str = "") -> Path:
    """Write approval status for ticket."""
    return TicketStateManager.write_approval_status(ticket_id, approved, approved_by, notes)


def list_all_tickets() -> Dict[str, Dict[str, Any]]:
    """List all tickets in index."""
    return TicketStateManager.get_all_tickets()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        TicketStateManager.migrate_singleton_files()
    else:
        print("Usage: python state_manager.py [migrate]")
