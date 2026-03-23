#!/usr/bin/env python3
"""Validate generated conversion artifacts for naming and EMR guard contracts."""

import argparse
import json
import pathlib
import re
import sys
from typing import List, Tuple

RULE_PATTERN = re.compile(
    r"^Year\d{4}\.Mips\d{1,4}\.[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*(?:\.EMR(?:\.(?:Org|Group|Provider))?)?$"
)
TICKET_STYLE_RULE_PATTERN = re.compile(r"^\d{4,}_[a-z0-9_]+$")
MARKER_PATTERN = re.compile(r"^Year\d{4}Mips\d{1,4}[A-Za-z0-9]+EMR(?:Org|Group|Provider)?$")
TICKET_STYLE_MARKER_PATTERN = re.compile(r"^T\d{4,}_.+")
FORBIDDEN_WRAPPER_DECLARE_PATTERN = re.compile(
    r"^(?:M\d+|Measure\d+|[A-Za-z0-9]+)(?:Context|Evidence|EmrOutput|OutputContext)$"
)


def load_extraction(ticket_id: str, root: pathlib.Path) -> dict:
    extraction_path = root / "artifacts" / "extraction" / f"{ticket_id}.json"
    if not extraction_path.exists():
        raise FileNotFoundError(f"Missing extraction artifact: {extraction_path}")
    with extraction_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_mips_drl_name_from_cql_basename(basename: str) -> str:
    stem = pathlib.Path(basename).stem
    stem_lower = stem.lower()

    if stem_lower.startswith("mips"):
        suffix = stem[len("mips") :]
        if suffix.isdigit():
            return f"mips{suffix}.drl"
        return f"{stem_lower}.drl"

    if stem.isdigit():
        return f"mips{stem}.drl"

    return pathlib.Path(basename).with_suffix(".drl").name


def expected_drl_paths(extraction: dict, root: pathlib.Path) -> List[pathlib.Path]:
    files = extraction.get("files", [])
    output_paths: List[pathlib.Path] = []
    for file_info in files:
        src_path = file_info.get("path", "")
        basename = pathlib.Path(src_path).name
        if not basename.lower().endswith(".cql"):
            continue
        drl_name = canonical_mips_drl_name_from_cql_basename(basename)
        output_paths.append(root / "artifacts" / "conversion" / drl_name)
    return output_paths


def legacy_duplicate_drl_paths(extraction: dict, root: pathlib.Path) -> List[pathlib.Path]:
    files = extraction.get("files", [])
    duplicates: List[pathlib.Path] = []
    for file_info in files:
        src_path = file_info.get("path", "")
        basename = pathlib.Path(src_path).name
        if not basename.lower().endswith(".cql"):
            continue

        canonical_name = canonical_mips_drl_name_from_cql_basename(basename)
        legacy_name = pathlib.Path(basename).with_suffix(".drl").name

        if canonical_name == legacy_name:
            continue

        legacy_path = root / "artifacts" / "conversion" / legacy_name
        if legacy_path.exists():
            duplicates.append(legacy_path)

    return duplicates


def parse_declares(text: str) -> List[str]:
    return re.findall(r"^declare\s+([A-Za-z0-9_]+)", text, flags=re.MULTILINE)


def parse_rules(text: str) -> List[str]:
    # Rule names can be wrapped in either single or double quotes.
    return re.findall(r"^rule\s+[\"']([^\"']+)[\"']", text, flags=re.MULTILINE)


def emr_rule_has_guard(text: str, rule_name: str) -> bool:
    block_match = re.search(
        rf"rule\s+[\"']{re.escape(rule_name)}[\"'](?P<body>.*?)\nend",
        text,
        flags=re.DOTALL,
    )
    if not block_match:
        return False
    body = block_match.group("body")
    has_guard_not_exists = re.search(r"not\s*\(\s*exists\s+[A-Za-z0-9_]+\s*\(\s*\)\s*\)", body)
    has_guard_not_fact = re.search(r"\n\s*not\s+[A-Za-z0-9_]+\s*\(\s*\)", body)
    has_marker_insert = re.search(r"insert\s*\(\s*new\s+[A-Za-z0-9_]+\s*\(\s*\)\s*\)", body)
    return bool((has_guard_not_exists or has_guard_not_fact) and has_marker_insert)


def has_placeholder_only_logic(text: str, rule_name: str) -> bool:
    block_match = re.search(
        rf"rule\s+[\"']{re.escape(rule_name)}[\"'](?P<body>.*?)\nend",
        text,
        flags=re.DOTALL,
    )
    if not block_match:
        return False

    body = block_match.group("body")
    normalized = re.sub(r"\s+", " ", body).strip().lower()
    if "eval(true)" in normalized:
        return True

    # Catch effectively empty rule skeletons with no predicates or actions.
    return normalized in {"when then", "when then ;"}


def validate_drl(path: pathlib.Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not path.exists():
        errors.append(f"Missing expected DRL artifact: {path}")
        return errors, warnings

    text = path.read_text(encoding="utf-8")
    declares = parse_declares(text)
    rules = parse_rules(text)

    if "import com.ablehealth.model.*" not in text:
        warnings.append(f"Missing reference import in {path}: import com.ablehealth.model.*")
    if "global PatientResults controlSet;" not in text:
        warnings.append(f"Missing reference global in {path}: global PatientResults controlSet;")
    if "EncounterDenominator(" not in text:
        warnings.append(f"No EncounterDenominator usage found in {path}; verify denominator handoff pattern")

    if not rules:
        errors.append(f"No rules found in {path}")

    for rule_name in rules:
        if TICKET_STYLE_RULE_PATTERN.match(rule_name):
            errors.append(f"Ticket-style rule name found in {path}: {rule_name}")
        if not RULE_PATTERN.match(rule_name):
            errors.append(f"Rule name does not match contract in {path}: {rule_name}")
        if has_placeholder_only_logic(text, rule_name):
            errors.append(f"Placeholder-only rule logic found in {path}: {rule_name}")
        if ".EMR" in rule_name and not emr_rule_has_guard(text, rule_name):
            errors.append(f"EMR rule missing fire-once guard/marker insert in {path}: {rule_name}")

    for declare_name in declares:
        if FORBIDDEN_WRAPPER_DECLARE_PATTERN.match(declare_name):
            errors.append(f"Synthetic wrapper declare found in {path}: {declare_name}")
        if "EMR" not in declare_name:
            continue
        if TICKET_STYLE_MARKER_PATTERN.match(declare_name):
            errors.append(f"Ticket-style marker declare found in {path}: {declare_name}")
        if not MARKER_PATTERN.match(declare_name):
            warnings.append(f"Marker declare does not match recommended format in {path}: {declare_name}")

    if "addPatientEMR" not in text and "EmrOutput" not in text:
        warnings.append(f"No EMR emission call/payload found in {path}; confirm this measure should emit EMR")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate conversion DRL artifacts")
    parser.add_argument("--ticket", required=True, help="Ticket ID (for example 1048701)")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path. Defaults to current working directory.",
    )
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    ticket_id = str(args.ticket)

    try:
        extraction = load_extraction(ticket_id, root)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    paths = expected_drl_paths(extraction, root)
    if not paths:
        print("ERROR: No changed CQL files found in extraction artifact")
        return 2

    duplicate_legacy_paths = legacy_duplicate_drl_paths(extraction, root)

    all_errors: List[str] = []
    all_warnings: List[str] = []

    for drl_path in paths:
        errors, warnings = validate_drl(drl_path)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    for warning in all_warnings:
        print(f"WARNING: {warning}")

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}")
        return 1

    if duplicate_legacy_paths:
        for legacy_path in duplicate_legacy_paths:
            print(
                "ERROR: Legacy duplicate DRL artifact found alongside canonical mips output: "
                f"{legacy_path}"
            )
        return 1

    print(f"Validation passed for ticket {ticket_id}: {len(paths)} DRL artifact(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
