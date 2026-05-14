"""``Import`` — tree-sitter node types for import / include / require statements.

Each grammar emits its own shape for "this file consumes this module":

  - Python: ``import_statement`` + ``import_from_statement``
  - JavaScript / TypeScript: ``import_statement`` (``source`` string field)
  - Go: ``import_spec`` (one entry per import; ``import_declaration``
    wraps a block of these)
  - Java: ``import_declaration``
  - C#: ``using_directive``
  - Julia: ``using_statement`` + ``import_statement``
  - C / C++: ``preproc_include`` (header inclusion is the closest analogue;
    the actual ``module`` text comes from ``string_literal`` or
    ``system_lib_string`` children)
  - Ruby: ``call`` whose method-identifier is ``require`` / ``require_relative``
    / ``load`` (Ruby imports are method calls, not statements — captured
    via tree-sitter predicate, not a dedicated node type)
  - Rust: ``use_declaration``

The walker queries each grammar's ``import_queries()`` rather than
matching node types directly, because tree-sitter captures (e.g.
``@module``) extract the module-string from a nested child. This enum
documents the canonical statement-level types for reference.
"""
from __future__ import annotations

from enum import StrEnum


class Import(StrEnum):
    IMPORT_STATEMENT = "import_statement"
    IMPORT_FROM_STATEMENT = "import_from_statement"
    IMPORT_DECLARATION = "import_declaration"
    IMPORT_SPEC = "import_spec"
    USING_DIRECTIVE = "using_directive"
    USING_STATEMENT = "using_statement"
    PREPROC_INCLUDE = "preproc_include"
    USE_DECLARATION = "use_declaration"
