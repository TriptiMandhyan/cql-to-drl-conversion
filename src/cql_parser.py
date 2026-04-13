"""
CQL (Clinical Quality Language) Parser.

Parses CQL source into a structured representation that can be used
for DRL (Drools Rule Language) generation.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CQLLibrary:
    """Represents a parsed CQL library."""

    name: str = ""
    version: str = ""
    using: str = ""
    using_version: str = ""
    includes: List[Dict[str, str]] = field(default_factory=list)
    codesystems: Dict[str, str] = field(default_factory=dict)
    valuesets: Dict[str, str] = field(default_factory=dict)
    codes: Dict[str, Dict[str, str]] = field(default_factory=dict)
    parameters: Dict[str, str] = field(default_factory=dict)
    context: str = "Patient"
    definitions: List[Dict[str, str]] = field(default_factory=list)
    functions: List[Dict[str, str]] = field(default_factory=list)


class CQLParser:
    """
    Parses CQL source text into a CQLLibrary object.

    Supports the following CQL constructs:
    - Library declaration
    - Using (FHIR model)
    - Include statements
    - Code system declarations
    - Value set declarations
    - Code declarations
    - Parameter declarations
    - Context declarations
    - Define statements
    - Function definitions
    """

    # Regex patterns for CQL constructs
    _LIBRARY_RE = re.compile(
        r"^\s*library\s+(\S+)\s+version\s+'([^']+)'", re.MULTILINE
    )
    _USING_RE = re.compile(
        r"^\s*using\s+(\S+)\s+version\s+'([^']+)'", re.MULTILINE
    )
    _INCLUDE_RE = re.compile(
        r"^\s*include\s+(\S+)\s+version\s+'([^']+)'\s+called\s+(\S+)",
        re.MULTILINE,
    )
    _CODESYSTEM_RE = re.compile(
        r"""^\s*codesystem\s+"([^"]+)"\s*:\s*'([^']+)'""", re.MULTILINE
    )
    _VALUESET_RE = re.compile(
        r"""^\s*valueset\s+"([^"]+)"\s*:\s*'([^']+)'""", re.MULTILINE
    )
    _CODE_RE = re.compile(
        r"""^\s*code\s+"([^"]+)"\s*:\s*'([^']+)'\s+from\s+(\S+)(?:\s+display\s+'([^']*)')?""",
        re.MULTILINE,
    )
    _PARAMETER_RE = re.compile(
        r"""^\s*parameter\s+"([^"]+)"\s+(.+)""", re.MULTILINE
    )
    _CONTEXT_RE = re.compile(r"^\s*context\s+(\S+)", re.MULTILINE)
    _DEFINE_RE = re.compile(
        r"""^\s*define\s+"([^"]+)"\s*:\s*([\s\S]*?)(?=\n\s*(?:define|function|context|parameter|$))""",
        re.MULTILINE,
    )
    _FUNCTION_RE = re.compile(
        r"""^\s*define\s+function\s+"([^"]+)"\s*\(([^)]*)\)\s*:\s*([\s\S]*?)(?=\n\s*(?:define|function|context|parameter|$))""",
        re.MULTILINE,
    )

    def parse(self, source: str) -> CQLLibrary:
        """
        Parse CQL source text into a CQLLibrary.

        Args:
            source: The CQL source code as a string.

        Returns:
            A CQLLibrary instance containing parsed constructs.

        Raises:
            ValueError: If the CQL source cannot be parsed.
        """
        library = CQLLibrary()

        # Normalize line endings
        source = source.replace("\r\n", "\n").replace("\r", "\n")

        self._parse_library_header(source, library)
        self._parse_using(source, library)
        self._parse_includes(source, library)
        self._parse_codesystems(source, library)
        self._parse_valuesets(source, library)
        self._parse_codes(source, library)
        self._parse_parameters(source, library)
        self._parse_context(source, library)
        self._parse_functions(source, library)
        self._parse_defines(source, library)

        return library

    def _parse_library_header(self, source: str, library: CQLLibrary) -> None:
        match = self._LIBRARY_RE.search(source)
        if match:
            library.name = match.group(1)
            library.version = match.group(2)

    def _parse_using(self, source: str, library: CQLLibrary) -> None:
        match = self._USING_RE.search(source)
        if match:
            library.using = match.group(1)
            library.using_version = match.group(2)

    def _parse_includes(self, source: str, library: CQLLibrary) -> None:
        for match in self._INCLUDE_RE.finditer(source):
            library.includes.append(
                {
                    "library": match.group(1),
                    "version": match.group(2),
                    "alias": match.group(3),
                }
            )

    def _parse_codesystems(self, source: str, library: CQLLibrary) -> None:
        for match in self._CODESYSTEM_RE.finditer(source):
            library.codesystems[match.group(1)] = match.group(2)

    def _parse_valuesets(self, source: str, library: CQLLibrary) -> None:
        for match in self._VALUESET_RE.finditer(source):
            library.valuesets[match.group(1)] = match.group(2)

    def _parse_codes(self, source: str, library: CQLLibrary) -> None:
        for match in self._CODE_RE.finditer(source):
            library.codes[match.group(1)] = {
                "code": match.group(2),
                "system": match.group(3),
                "display": match.group(4) or "",
            }

    def _parse_parameters(self, source: str, library: CQLLibrary) -> None:
        for match in self._PARAMETER_RE.finditer(source):
            library.parameters[match.group(1)] = match.group(2).strip()

    def _parse_context(self, source: str, library: CQLLibrary) -> None:
        match = self._CONTEXT_RE.search(source)
        if match:
            library.context = match.group(1)

    def _parse_functions(self, source: str, library: CQLLibrary) -> None:
        for match in self._FUNCTION_RE.finditer(source):
            library.functions.append(
                {
                    "name": match.group(1),
                    "params": match.group(2).strip(),
                    "body": match.group(3).strip(),
                }
            )

    def _parse_defines(self, source: str, library: CQLLibrary) -> None:
        # Collect names of already-parsed functions to skip them
        function_names = {f["name"] for f in library.functions}

        # Split source into blocks by top-level keywords to parse defines
        # We look for define statements that are NOT define function
        define_pattern = re.compile(
            r"""^\s*define\s+"([^"]+)"\s*:""", re.MULTILINE
        )
        # Find all define positions (excluding functions)
        positions = []
        for m in define_pattern.finditer(source):
            name = m.group(1)
            # Check if this define is actually a function definition
            before_colon = source[m.start(): m.end()]
            if "function" in before_colon:
                continue
            if name not in function_names:
                positions.append((m.start(), m.end(), name))

        # Extract body for each define (up to next top-level keyword or EOF)
        top_level_kw = re.compile(
            r"^\s*(?:define|library|using|include|codesystem|valueset|code|parameter|context)\b",
            re.MULTILINE,
        )

        for i, (start, end, name) in enumerate(positions):
            # Find next top-level keyword after this define
            body_start = end
            next_kw = None
            for m in top_level_kw.finditer(source, body_start):
                next_kw = m.start()
                break

            body = source[body_start:next_kw].strip() if next_kw else source[body_start:].strip()

            library.definitions.append({"name": name, "expression": body})
