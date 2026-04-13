"""Integration tests for CQLToDRLConverter."""

import pytest
from pathlib import Path

from src.converter import CQLToDRLConverter


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestCQLToDRLConverter:
    def setup_method(self):
        self.converter = CQLToDRLConverter()

    def test_convert_returns_string(self):
        cql = "library T version '1.0.0'\ncontext Patient\n"
        result = self.converter.convert(cql)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_empty_source(self):
        result = self.converter.convert("")
        assert isinstance(result, str)

    def test_convert_with_custom_package(self):
        converter = CQLToDRLConverter(package="org.myorg.rules")
        cql = "library T version '1.0.0'\ncontext Patient\n"
        result = converter.convert(cql)
        assert "package org.myorg.rules;" in result

    def test_convert_diabetes_example(self):
        cql_path = EXAMPLES_DIR / "diabetes_screening.cql"
        drl = self.converter.convert_file(str(cql_path))

        # Package and imports
        assert "package com.cql.drl;" in drl
        assert "import org.hl7.fhir.r4.model.Patient;" in drl

        # Library header comment
        assert "DiabetesScreening" in drl

        # Rules generated for each define
        assert 'rule "Initial Population"' in drl
        assert 'rule "Has Diabetes Diagnosis"' in drl
        assert 'rule "Needs HbA1c Test"' in drl
        assert 'rule "Denominator"' in drl
        assert 'rule "Numerator"' in drl

    def test_convert_hypertension_example(self):
        cql_path = EXAMPLES_DIR / "hypertension_check.cql"
        drl = self.converter.convert_file(str(cql_path))

        assert "HypertensionCheck" in drl
        assert 'rule "Initial Population"' in drl
        assert 'rule "Has Hypertension"' in drl
        assert 'rule "Denominator"' in drl
        assert 'rule "Numerator"' in drl

    def test_convert_file_writes_output(self, tmp_path):
        cql_path = EXAMPLES_DIR / "diabetes_screening.cql"
        output_path = tmp_path / "output.drl"

        drl = self.converter.convert_file(str(cql_path), str(output_path))

        assert output_path.exists()
        written = output_path.read_text(encoding="utf-8")
        assert written == drl

    def test_convert_file_without_output_path(self):
        cql_path = EXAMPLES_DIR / "diabetes_screening.cql"
        drl = self.converter.convert_file(str(cql_path))
        assert isinstance(drl, str)
        assert len(drl) > 0

    def test_convert_all_rules_have_when_then_end(self):
        cql = (
            "library T version '1.0.0'\n"
            "context Patient\n"
            "define \"A\": AgeInYears() >= 18\n"
            "define \"B\": AgeInYears() < 65\n"
        )
        drl = self.converter.convert(cql)
        # Count rule blocks
        rule_count = drl.count("\nrule ")
        when_count = drl.count("\n    when")
        then_count = drl.count("\n    then")
        end_count = drl.count("\nend")
        assert rule_count == when_count == then_count == end_count

    def test_roundtrip_produces_deterministic_output(self):
        cql_path = EXAMPLES_DIR / "diabetes_screening.cql"
        drl1 = self.converter.convert_file(str(cql_path))
        drl2 = self.converter.convert_file(str(cql_path))
        assert drl1 == drl2
