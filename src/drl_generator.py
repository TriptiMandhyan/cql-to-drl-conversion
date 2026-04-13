"""
DRL (Drools Rule Language) Generator.

Converts a parsed CQLLibrary into DRL rule source text.
"""

import re
from typing import List

from .cql_parser import CQLLibrary


class DRLGenerator:
    """
    Generates DRL source text from a parsed CQLLibrary.

    The generated DRL is compatible with Drools 7.x / 8.x and uses
    FHIR R4 data model classes from the hapi-fhir library.
    """

    # Default Java package for generated rules
    DEFAULT_PACKAGE = "com.cql.drl"

    # Default FHIR imports used by the generated rules
    _FHIR_IMPORTS = [
        "org.hl7.fhir.r4.model.Patient",
        "org.hl7.fhir.r4.model.Condition",
        "org.hl7.fhir.r4.model.Observation",
        "org.hl7.fhir.r4.model.MedicationRequest",
        "org.hl7.fhir.r4.model.Encounter",
        "org.hl7.fhir.r4.model.Procedure",
        "org.hl7.fhir.r4.model.CodeableConcept",
        "org.hl7.fhir.r4.model.Coding",
        "java.util.List",
        "java.util.Date",
    ]

    def generate(self, library: CQLLibrary, package: str = "") -> str:
        """
        Generate DRL source text from a parsed CQLLibrary.

        Args:
            library: The parsed CQL library to convert.
            package: Optional Java package name. Defaults to DEFAULT_PACKAGE.

        Returns:
            A string containing the generated DRL source.
        """
        package = package or self.DEFAULT_PACKAGE
        sections: List[str] = []

        sections.append(self._generate_header(library, package))
        sections.append(self._generate_imports())
        sections.append(self._generate_globals(library))
        sections.append(self._generate_functions(library))
        sections.append(self._generate_rules(library))

        return "\n".join(filter(None, sections))

    # ------------------------------------------------------------------
    # Header & metadata
    # ------------------------------------------------------------------

    def _generate_header(self, library: CQLLibrary, package: str) -> str:
        lines = [f"package {package};", ""]
        if library.name:
            lines.append(
                f"// CQL Library: {library.name} v{library.version}"
            )
        if library.using:
            lines.append(
                f"// Using: {library.using} v{library.using_version}"
            )
        for inc in library.includes:
            lines.append(
                f"// Include: {inc['library']} v{inc['version']} as {inc['alias']}"
            )
        if len(lines) > 2:
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def _generate_imports(self) -> str:
        lines = [f"import {cls};" for cls in self._FHIR_IMPORTS]
        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Globals (value-sets and parameters become DRL globals)
    # ------------------------------------------------------------------

    def _generate_globals(self, library: CQLLibrary) -> str:
        lines: List[str] = []

        for name, url in library.valuesets.items():
            safe = self._safe_id(name)
            lines.append(f'// ValueSet "{name}": {url}')
            lines.append(f"global java.util.Set {safe};")

        for name, type_str in library.parameters.items():
            safe = self._safe_id(name)
            java_type = self._cql_type_to_java(type_str)
            lines.append(f'// Parameter "{name}"')
            lines.append(f"global {java_type} {safe};")

        if lines:
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helper functions (CQL define functions become DRL functions)
    # ------------------------------------------------------------------

    def _generate_functions(self, library: CQLLibrary) -> str:
        if not library.functions:
            return ""
        lines: List[str] = []
        for func in library.functions:
            name = self._safe_id(func["name"])
            params = self._convert_function_params(func["params"])
            body = self._convert_expression(func["body"], library)
            lines.append(f"function Object {name}({params}) {{")
            lines.append(f"    return {body};")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Rules (each CQL define becomes a Drools rule)
    # ------------------------------------------------------------------

    def _generate_rules(self, library: CQLLibrary) -> str:
        lines: List[str] = []
        for definition in library.definitions:
            lines.append(self._generate_rule(definition, library))
        return "\n".join(lines)

    def _generate_rule(
        self, definition: dict, library: CQLLibrary
    ) -> str:
        name = definition["name"]
        expression = definition["expression"]

        condition = self._convert_to_condition(expression, library)
        action = self._build_action(name)

        lines = [
            f'rule "{name}"',
            "    when",
        ]
        for cond_line in condition.splitlines():
            lines.append(f"        {cond_line}")
        lines += [
            "    then",
            f"        {action}",
            "end",
            "",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Expression conversion
    # ------------------------------------------------------------------

    def _convert_to_condition(
        self, expression: str, library: CQLLibrary
    ) -> str:
        """Convert a CQL expression to a DRL 'when' condition block."""
        expr = expression.strip()

        # exists ([ResourceType: "ValueSet"])
        exists_valueset = re.match(
            r'exists\s*\(\s*\[([^:]+):\s*"([^"]+)"\s*\]\s*\)', expr
        )
        if exists_valueset:
            resource = exists_valueset.group(1).strip()
            vs_name = exists_valueset.group(2).strip()
            vs_id = self._safe_id(vs_name)
            return (
                f"{resource}(coding: coding)\n"
                f"    eval(coding.stream().anyMatch(c -> {vs_id} != null && {vs_id}.contains(c.getCode())))"
            )

        # exists ([ResourceType])
        exists_resource = re.match(
            r'exists\s*\(\s*\[([^\]]+)\]\s*\)', expr
        )
        if exists_resource:
            resource = exists_resource.group(1).strip()
            return f"{resource}()"

        # not exists
        not_exists_resource = re.match(
            r'not\s+exists\s*\(\s*\[([^\]]+)\]\s*\)', expr
        )
        if not_exists_resource:
            resource = not_exists_resource.group(1).strip()
            return f"not {resource}()"

        # Age comparison: AgeInYears() >= N
        age_compare = re.search(
            r'AgeInYears\(\)\s*([><=!]+)\s*(\d+)', expr
        )
        if age_compare:
            op = age_compare.group(1)
            years = age_compare.group(2)
            return f"Patient(eval(calculateAge(birthDate) {op} {years}))"

        # Boolean literals
        if expr.lower() == "true":
            return "eval(true)"
        if expr.lower() == "false":
            return "eval(false)"

        # Fallback: wrap as an eval with the converted expression
        converted = self._convert_expression(expr, library)
        return f"eval({converted})"

    def _convert_expression(
        self, expression: str, library: CQLLibrary
    ) -> str:
        """Convert a CQL expression to a Java/DRL expression."""
        expr = expression.strip()

        # Boolean operators
        expr = re.sub(r'\band\b', "&&", expr)
        expr = re.sub(r'\bor\b', "||", expr)
        expr = re.sub(r'\bnot\b', "!", expr)

        # Null checks
        expr = re.sub(r'\bis null\b', "== null", expr)
        expr = re.sub(r'\bis not null\b', "!= null", expr)

        # Date arithmetic: X - N years  →  subtract years
        expr = re.sub(
            r'Today\(\)\s*-\s*(\d+)\s+years?',
            r'java.time.LocalDate.now().minusYears(\1)',
            expr,
        )
        expr = re.sub(r'\bToday\(\)', "java.time.LocalDate.now()", expr)
        expr = re.sub(r'\bNow\(\)', "new java.util.Date()", expr)

        # Patient.birthDate
        expr = re.sub(r'\bPatient\.birthDate\b', "patient.getBirthDate()", expr)

        # exists ([Resource])
        expr = re.sub(
            r'exists\s*\(\s*\[([^\]]+)\]\s*\)',
            r'/* exists \1 */',
            expr,
        )

        # Quoted names → safe Java identifiers
        expr = re.sub(r'"([^"]+)"', lambda m: self._safe_id(m.group(1)), expr)

        return expr

    def _convert_function_params(self, params_str: str) -> str:
        """Convert CQL function parameter list to Java parameter list."""
        if not params_str.strip():
            return ""
        parts = []
        for param in params_str.split(","):
            param = param.strip()
            if " " in param:
                tokens = param.rsplit(" ", 1)
                java_type = self._cql_type_to_java(tokens[0].strip())
                name = self._safe_id(tokens[1].strip())
                parts.append(f"{java_type} {name}")
            else:
                parts.append(f"Object {self._safe_id(param)}")
        return ", ".join(parts)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _build_action(self, rule_name: str) -> str:
        safe = self._safe_id(rule_name)
        return (
            f'System.out.println("Rule \\"{rule_name}\\" fired for context: " + drools.getRule().getName());'
        )

    @staticmethod
    def _safe_id(name: str) -> str:
        """Convert a CQL name to a safe Java identifier."""
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if safe and safe[0].isdigit():
            safe = "_" + safe
        return safe

    @staticmethod
    def _cql_type_to_java(cql_type: str) -> str:
        """Map a CQL type annotation to a Java type."""
        mapping = {
            "Integer": "int",
            "Decimal": "double",
            "Boolean": "boolean",
            "String": "String",
            "Date": "java.time.LocalDate",
            "DateTime": "java.util.Date",
            "Quantity": "double",
            "Interval<Date>": "java.time.LocalDate[]",
            "Interval<DateTime>": "java.util.Date[]",
        }
        return mapping.get(cql_type.strip(), "Object")
