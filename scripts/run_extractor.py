#!/usr/bin/env python3
"""Backward-compatible wrapper for the consolidated fallback utility.

Prefer `scripts/ado_fallback.py` for all non-MCP retrieval/extraction operations.
This wrapper remains to avoid breaking older commands.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticket-id", default="")
    parser.add_argument("--intake-path", default="")
    parser.add_argument("--output-manifest", default="")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    fallback_script = Path(__file__).with_name("ado_fallback.py")
    cmd = [
        sys.executable,
        str(fallback_script),
        "run-extraction",
    ]

    if args.ticket_id:
        cmd.extend(["--ticket-id", args.ticket_id])
    if args.intake_path:
        cmd.extend(["--intake", args.intake_path])
    if args.output_manifest:
        cmd.extend(["--fetched-out", args.output_manifest])
    if args.output_dir:
        cmd.extend(["--raw-dir", args.output_dir])

    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
