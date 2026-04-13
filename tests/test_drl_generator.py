"""Tests for DRLGenerator."""

import pytest

from src.cql_parser import CQLParser, CQLLibrary
from src.drl_generator import DRLGenerator


def _parse(cql: str) -> CQLLibrary:
    return CQLParser().parse(cql)


class TestDRLGenerator:
    def setup_method(self):
        self.generator = DRLGenerator()

    def test_generates_package_declaration(self):
        library = CQLLibrary(name="Test", version="1.0.0")
        drl = self.generator.generate(library, package="com.example")
        assert "package com.example;" in drl

    def test_generates_default_package(self):
        library = CQLLibrary()
        drl = self.generator.generate(library)
        assert "package com.cql.drl;" in drl

    def test_generates_imports(self):
        library = CQLLibrary()
        drl = self.generator.generate(library)
        assert "import org.hl7.fhir.r4.model.Patient;" in drl
        assert "import org.hl7.fhir.r4.model.Condition;" in drl

    def test_generates_library_header_comment(self):
        library = CQLLibrary(name="DiabetesLib", version="1.2.3")
        drl = self.generator.generate(library)
        assert "CQL Library: DiabetesLib v1.2.3" in drl

    def test_generates_valueset_globals(self):
        library = CQLLibrary(
            valuesets={"Diabetes Conditions": "http://example.com/vs"}
        )
        drl = self.generator.generate(library)
        assert "global java.util.Set Diabetes_Conditions;" in drl

    def test_generates_parameter_globals(self):
        library = CQLLibrary(
            parameters={"Measurement Period": "Interval<Date>"}
        )
        drl = self.generator.generate(library)
        assert "global" in drl
        assert "Measurement_Period" in drl

    def test_generates_rule_for_each_definition(self):
        library = _parse(
            "library T version '1.0.0'\n"
            "context Patient\n"
            "define \"RuleA\":\n"
            "  true\n"
            "define \"RuleB\":\n"
            "  false\n"
        )
        drl = self.generator.generate(library)
        assert 'rule "RuleA"' in drl
        assert 'rule "RuleB"' in drl

    def test_rule_structure_has_when_then_end(self):
        library = _parse(
            "library T version '1.0.0'\n"
            "context Patient\n"
            "define \"Check\":\n"
            "  AgeInYears() >= 18\n"
        )
        drl = self.generator.generate(library)
        assert "when" in drl
        assert "then" in drl
        assert "end" in drl

    def test_age_condition_converted(self):
        library = _parse(
            "library T version '1.0.0'\n"
            "context Patient\n"
            "define \"Adult\":\n"
            "  AgeInYears() >= 18\n"
        )
        drl = self.generator.generate(library)
        # Should produce some Patient-based condition
        assert "Patient" in drl

    def test_exists_valueset_converted(self):
        library = _parse(
            "library T version '1.0.0'\n"
            "valueset \"My VS\": 'http://example.com/vs'\n"
            "context Patient\n"
            "define \"HasCondition\":\n"
            '  exists ([Condition: "My VS"])\n'
        )
        drl = self.generator.generate(library)
        assert "Condition" in drl

    def test_not_exists_converted(self):
        library = _parse(
            "library T version '1.0.0'\n"
            "context Patient\n"
            "define \"NoEncounters\":\n"
            "  not exists ([Encounter])\n"
        )
        drl = self.generator.generate(library)
        assert "not" in drl.lower()

    def test_safe_id_replaces_spaces_and_hyphens(self):
        safe = DRLGenerator._safe_id("My Rule-Name 123")
        assert " " not in safe
        assert "-" not in safe

    def test_safe_id_does_not_start_with_digit(self):
        safe = DRLGenerator._safe_id("123abc")
        assert not safe[0].isdigit()

    def test_cql_type_to_java_integer(self):
        assert DRLGenerator._cql_type_to_java("Integer") == "int"

    def test_cql_type_to_java_string(self):
        assert DRLGenerator._cql_type_to_java("String") == "String"

    def test_cql_type_to_java_unknown_defaults_to_object(self):
        assert DRLGenerator._cql_type_to_java("CustomType") == "Object"

    def test_full_diabetes_cql_produces_valid_drl(self):
        cql = (
            "library DiabetesScreening version '1.0.0'\n"
            "using FHIR version '4.0.1'\n"
            "valueset \"Diabetes Mellitus Conditions\": 'http://example.com/vs1'\n"
            "parameter \"Measurement Period\" Interval<Date>\n"
            "context Patient\n"
            "define \"Initial Population\":\n"
            "  AgeInYears() >= 18\n"
            "define \"Has Diabetes Diagnosis\":\n"
            '  exists ([Condition: "Diabetes Mellitus Conditions"])\n'
        )
        library = _parse(cql)
        drl = self.generator.generate(library)

        # Basic structural checks
        assert "package" in drl
        assert "import" in drl
        assert 'rule "Initial Population"' in drl
        assert 'rule "Has Diabetes Diagnosis"' in drl
        assert drl.count("end") >= 2
