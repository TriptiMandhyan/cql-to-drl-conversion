"""
CQL to DRL Converter.

High-level API that ties together the CQL parser and DRL generator.
"""

import sys
from pathlib import Path
from typing import Optional

from .cql_parser import CQLParser
from .drl_generator import DRLGenerator


class CQLToDRLConverter:
    """
    Converts CQL (Clinical Quality Language) source to DRL (Drools Rule Language).

    Usage::

        converter = CQLToDRLConverter()
        drl = converter.convert(cql_source)

    Or convert files directly::

        converter = CQLToDRLConverter()
        converter.convert_file("my_library.cql", "my_library.drl")
    """

    def __init__(self, package: str = "") -> None:
        """
        Initialise the converter.

        Args:
            package: Java package name for the generated DRL file.
                     Defaults to ``com.cql.drl``.
        """
        self._parser = CQLParser()
        self._generator = DRLGenerator()
        self._package = package

    def convert(self, cql_source: str) -> str:
        """
        Convert a CQL source string to DRL.

        Args:
            cql_source: The CQL source code as a string.

        Returns:
            The generated DRL source as a string.
        """
        library = self._parser.parse(cql_source)
        return self._generator.generate(library, package=self._package)

    def convert_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Convert a CQL file to DRL and optionally write the result to disk.

        Args:
            input_path: Path to the input ``.cql`` file.
            output_path: Path where the ``.drl`` file should be written.
                         If omitted, the result is only returned but not saved.

        Returns:
            The generated DRL source as a string.
        """
        cql_source = Path(input_path).read_text(encoding="utf-8")
        drl = self.convert(cql_source)

        if output_path:
            Path(output_path).write_text(drl, encoding="utf-8")

        return drl


def main() -> None:
    """Command-line entry point: ``cql2drl <input.cql> [output.drl]``."""
    if len(sys.argv) < 2:
        print("Usage: cql2drl <input.cql> [output.drl]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    converter = CQLToDRLConverter()
    drl = converter.convert_file(input_path, output_path)

    if output_path:
        print(f"DRL written to: {output_path}")
    else:
        print(drl)


if __name__ == "__main__":
    main()
