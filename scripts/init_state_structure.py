#!/usr/bin/env python3
"""
Initialize state directory structure for multi-ticket workflow.

Creates the per-ticket state directories and master index if they don't exist.
"""

import json
from pathlib import Path
from datetime import datetime


def init_state_structure():
    """Initialize base state directory structure."""
    
    # Create state/tickets directory
    tickets_dir = Path("state/tickets")
    tickets_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created directory: {tickets_dir}")
    
    # Create master index if it doesn't exist
    index_file = tickets_dir / "index.json"
    if not index_file.exists():
        index_data = {
            "currentTicketId": None,
            "lastUpdated": datetime.now().isoformat(),
            "tickets": {}
        }
        index_file.write_text(json.dumps(index_data, indent=2))
        print(f"✓ Created file: {index_file}")
    else:
        print(f"  (already exists: {index_file})")
    
    # Ensure run-input.json exists with template
    run_input_file = Path("state/run-input.json")
    if not run_input_file.exists():
        run_input_data = {
            "ticketId": "",
            "ticketUrl": "",
            "description": "Set ticketId or ticketUrl before running agents"
        }
        run_input_file.write_text(json.dumps(run_input_data, indent=2))
        print(f"✓ Created file: {run_input_file}")
        print(f"  ⚠ Set ticketId or ticketUrl before running agents")
    else:
        print(f"  (already exists: {run_input_file})")
    
    print("\n✓ State directory structure initialized successfully!")
    print(f"\nNext steps:")
    print(f"1. Edit state/run-input.json and set ticketId or ticketUrl")
    print(f"2. Start local MCP server: python scripts/local_mcp_server.py")
    print(f"3. Run first agent: /ticketDescriptionIntakeAgent")


if __name__ == "__main__":
    import sys
    try:
        init_state_structure()
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
