"""Tests for CQLParser."""

import pytest

from src.cql_parser import CQLParser, CQLLibrary


DIABETES_CQL = """
library DiabetesScreening version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1' called FHIRHelpers

codesystem "SNOMED-CT": 'http://snomed.info/sct'

valueset "Diabetes Mellitus Conditions": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.464.1003.103.12.1001'

code "Diabetes type 2": '44054006' from "SNOMED-CT" display 'Diabetes mellitus type 2'

parameter "Measurement Period" Interval<Date>

context Patient

define "Initial Population":
  AgeInYears() >= 18

define "Has Diabetes Diagnosis":
  exists ([Condition: "Diabetes Mellitus Conditions"])
"""


class TestCQLParser:
    def setup_method(self):
        self.parser = CQLParser()

    def test_parses_library_name_and_version(self):
        library = self.parser.parse(DIABETES_CQL)
        assert library.name == "DiabetesScreening"
        assert library.version == "1.0.0"

    def test_parses_using_clause(self):
        library = self.parser.parse(DIABETES_CQL)
        assert library.using == "FHIR"
        assert library.using_version == "4.0.1"

    def test_parses_includes(self):
        library = self.parser.parse(DIABETES_CQL)
        assert len(library.includes) == 1
        assert library.includes[0]["library"] == "FHIRHelpers"
        assert library.includes[0]["version"] == "4.0.1"
        assert library.includes[0]["alias"] == "FHIRHelpers"

    def test_parses_codesystem(self):
        library = self.parser.parse(DIABETES_CQL)
        assert "SNOMED-CT" in library.codesystems
        assert library.codesystems["SNOMED-CT"] == "http://snomed.info/sct"

    def test_parses_valueset(self):
        library = self.parser.parse(DIABETES_CQL)
        assert "Diabetes Mellitus Conditions" in library.valuesets

    def test_parses_code(self):
        library = self.parser.parse(DIABETES_CQL)
        assert "Diabetes type 2" in library.codes
        code = library.codes["Diabetes type 2"]
        assert code["code"] == "44054006"
        assert code["system"] == '"SNOMED-CT"'
        assert code["display"] == "Diabetes mellitus type 2"

    def test_parses_parameter(self):
        library = self.parser.parse(DIABETES_CQL)
        assert "Measurement Period" in library.parameters
        assert "Interval" in library.parameters["Measurement Period"]

    def test_parses_context(self):
        library = self.parser.parse(DIABETES_CQL)
        assert library.context == "Patient"

    def test_parses_definitions(self):
        library = self.parser.parse(DIABETES_CQL)
        names = [d["name"] for d in library.definitions]
        assert "Initial Population" in names
        assert "Has Diabetes Diagnosis" in names

    def test_definition_expressions_are_not_empty(self):
        library = self.parser.parse(DIABETES_CQL)
        for defn in library.definitions:
            assert defn["expression"].strip() != "", (
                f"Expression for '{defn['name']}' must not be empty"
            )

    def test_empty_source_returns_default_library(self):
        library = self.parser.parse("")
        assert library.name == ""
        assert library.context == "Patient"
        assert library.definitions == []

    def test_library_without_version(self):
        source = "library MyLib version '0.1.0'\ncontext Patient\n"
        library = self.parser.parse(source)
        assert library.name == "MyLib"
        assert library.version == "0.1.0"

    def test_multiple_valuesets(self):
        source = (
            "library X version '1.0.0'\n"
            "valueset \"VS1\": 'http://example.com/vs1'\n"
            "valueset \"VS2\": 'http://example.com/vs2'\n"
            "context Patient\n"
        )
        library = self.parser.parse(source)
        assert "VS1" in library.valuesets
        assert "VS2" in library.valuesets

    def test_function_definitions_are_separated_from_defines(self):
        source = (
            "library F version '1.0.0'\n"
            "context Patient\n"
            "define function \"Double\"(x Integer):\n"
            "  x * 2\n"
            "define \"MyDefine\":\n"
            "  true\n"
        )
        library = self.parser.parse(source)
        func_names = [f["name"] for f in library.functions]
        def_names = [d["name"] for d in library.definitions]
        assert "Double" in func_names
        assert "MyDefine" in def_names
        assert "Double" not in def_names
