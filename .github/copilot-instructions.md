# CQL to DRL Conversion — Copilot Instructions

## Project overview

This repository contains a Python tool that converts
**Clinical Quality Language (CQL)** into **Drools Rule Language (DRL)**.

CQL is used to express clinical quality measures and decision support
logic for FHIR-based healthcare systems. DRL is the rule language used
by the [Drools](https://www.drools.org/) business-rules engine.

## Repository layout

```
src/
  cql_parser.py      – Parses CQL source into a CQLLibrary data class
  drl_generator.py   – Converts a CQLLibrary to DRL source text
  converter.py       – High-level CQLToDRLConverter API + CLI entry-point
tests/
  test_cql_parser.py
  test_drl_generator.py
  test_converter.py
examples/
  diabetes_screening.cql
  hypertension_check.cql
```

## Key conventions

- **Python 3.8+** – use standard-library modules only; no external runtime
  dependencies.
- **Dataclasses** for structured data (`CQLLibrary`).
- **`re` module** for parsing; avoid third-party parsers.
- **Pytest** for all tests; run with `pytest`.
- Generated DRL targets **Drools 7.x / 8.x** and assumes FHIR R4 classes
  from `hapi-fhir`.

## Skills

### `convert-cql-to-drl`

Convert a CQL snippet or file to DRL.

**Inputs**
- CQL source text **or** path to a `.cql` file.
- (Optional) Java package name for the output DRL (default: `com.cql.drl`).

**Steps**
1. Parse the CQL with `CQLParser.parse()`.
2. Generate DRL with `DRLGenerator.generate()`.
3. Return the DRL string (and optionally write to a `.drl` file).

**Example CLI usage**
```bash
cql2drl examples/diabetes_screening.cql output/diabetes_screening.drl
```

### `add-cql-define`

Add a new `define` statement to an existing CQL library and regenerate the
corresponding DRL rule.

**Inputs**
- Existing CQL source.
- Name and CQL expression for the new define.

**Steps**
1. Append the `define` block to the CQL source.
2. Re-parse and re-generate the DRL.
3. Return the updated CQL and DRL.

### `validate-cql-structure`

Check that a CQL source file contains well-formed constructs expected by
this converter (library header, context, at least one define).

**Inputs**
- CQL source text.

**Steps**
1. Parse with `CQLParser`.
2. Assert `library.name`, `library.context`, and `library.definitions`
   are non-empty.
3. Return a summary of what was found.

## How to run tests

```bash
pip install -r requirements.txt
pytest
```

## How to extend the converter

1. **New CQL construct** – add a regex pattern to `CQLParser` and populate
   the appropriate field on `CQLLibrary`.
2. **New DRL output** – add a `_generate_*` method to `DRLGenerator` and
   call it from `generate()`.
3. **New example** – add a `.cql` file under `examples/` and a corresponding
   assertion in `tests/test_converter.py`.
