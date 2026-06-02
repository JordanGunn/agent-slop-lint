"""NodeKind — the language-agnostic node vocabulary.

A small neutral enum naming the cross-language constructs the AST commits to.
The raw tree-sitter type -> ``NodeKind`` mapping is computed in ``tree.Node.kind``
from the *grammar's own* vocabulary methods (``callable()``, ``decision_nodes()``,
``loop_nodes()``, ...) — there is no separate table to drift, and the raw
``.type`` stays available as the escape hatch for the long tail.

(Revives the legacy ``slop.language.ast`` per-category node enums as one flat
neutral vocabulary rather than a module-per-category split.)
"""
from __future__ import annotations

from enum import Enum


class NodeKind(Enum):
    """Neutral categories for cross-language AST navigation."""

    CALLABLE = "callable"
    CLASS = "class"
    BRANCH = "branch"        # if / conditional
    LOOP = "loop"
    SWITCH = "switch"
    CASE = "case"
    TRY = "try"
    CATCH = "catch"
    CALL = "call"
    IDENTIFIER = "identifier"
    LITERAL = "literal"
    BOOLEAN_OP = "boolean_op"
    IMPORT = "import"
    PARAMETER = "parameter"
    OTHER = "other"
