# CQL to DRL Conversion

A Python tool that converts **Clinical Quality Language (CQL)** into
**Drools Rule Language (DRL)**.

## Background

| Term | Description |
|------|-------------|
| **CQL** | [Clinical Quality Language](https://cql.hl7.org/) — a high-level, domain-specific language for expressing clinical logic and quality measures in FHIR-based healthcare systems. |
| **DRL** | [Drools Rule Language](https://www.drools.org/) — the rule language used by the Drools business-rules engine (Java). |

## Features

- Parses CQL library headers, value sets, code systems, parameters, and `define` statements
- Converts each CQL `define` into a Drools `rule` block
- Maps value sets to DRL `global` declarations
- Generates FHIR R4 (hapi-fhir) compatible condition patterns
- Simple CLI: `cql2drl <input.cql> [output.drl]`

## Project structure

```
src/
  cql_parser.py       – CQL → CQLLibrary data class (regex-based parser)
  drl_generator.py    – CQLLibrary → DRL source text
  converter.py        – High-level API + CLI entry-point (cql2drl)
tests/
  test_cql_parser.py
  test_drl_generator.py
  test_converter.py
examples/
  diabetes_screening.cql
  hypertension_check.cql
.github/
  workflows/
    copilot-setup-steps.yml   – Copilot agent environment setup
  copilot-instructions.md     – Copilot skills and project instructions
```

## Quick start

```bash
# Install
pip install -r requirements.txt
pip install -e .

# Convert a CQL file to DRL (prints to stdout)
cql2drl examples/diabetes_screening.cql

# Convert and save to a file
cql2drl examples/diabetes_screening.cql output/diabetes_screening.drl
```

### Python API

```python
from src.converter import CQLToDRLConverter

converter = CQLToDRLConverter(package="com.myorg.rules")

with open("examples/diabetes_screening.cql") as f:
    cql = f.read()

drl = converter.convert(cql)
print(drl)
```

## Running tests

```bash
pytest
```

## Example

**Input** (`diabetes_screening.cql` excerpt):

```cql
library DiabetesScreening version '1.0.0'
using FHIR version '4.0.1'

valueset "Diabetes Mellitus Conditions": 'http://cts.nlm.nih.gov/...'

context Patient

define "Initial Population":
  AgeInYears() >= 18

define "Has Diabetes Diagnosis":
  exists ([Condition: "Diabetes Mellitus Conditions"])
```

**Output** (DRL):

```drl
package com.cql.drl;

// CQL Library: DiabetesScreening v1.0.0
// Using: FHIR v4.0.1

import org.hl7.fhir.r4.model.Patient;
import org.hl7.fhir.r4.model.Condition;
...

global java.util.Set Diabetes_Mellitus_Conditions;

rule "Initial Population"
    when
        Patient(eval(calculateAge(birthDate) >= 18))
    then
        System.out.println("Rule \"Initial Population\" fired ...");
end

rule "Has Diabetes Diagnosis"
    when
        Condition(coding: coding)
            eval(coding.stream().anyMatch(c -> Diabetes_Mellitus_Conditions != null && ...))
    then
        System.out.println("Rule \"Has Diabetes Diagnosis\" fired ...");
end
```

## Copilot agents & skills

This repository is configured for **GitHub Copilot cloud agent**:

- **`.github/workflows/copilot-setup-steps.yml`** — pre-installs Python and
  project dependencies so Copilot can run tests and the CLI tool immediately.
- **`.github/copilot-instructions.md`** — defines project conventions and
  Copilot skills (`convert-cql-to-drl`, `add-cql-define`,
  `validate-cql-structure`).
