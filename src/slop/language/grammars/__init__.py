"""Concrete grammar implementations + DEFAULT_GRAMMARS registry.

``DEFAULT_GRAMMARS`` maps file extension → grammar CLASS (not instance —
grammars are pure classmethod surfaces with no per-instance state).
``Tree`` consults it during ``scan()`` to dispatch each discovered
file to the right grammar's classmethods.

Auto-detect is the primary mode: callers do NOT declare which languages
they want linted. The registry ships fully populated. Advanced callers
can pass ``grammars=`` to ``Tree`` to override or extend.

Lazy loading: the underlying tree-sitter ``Language`` objects are
loaded on first call to ``cls.grammar()`` and cached by
``_ast/treesitter.py:_LANGUAGE_CACHE``. Languages absent from the
scanned corpus are never loaded.
"""
from __future__ import annotations

from ..base import Language
from .c import C
from .cpp import Cpp
from .csharp import CSharp
from .go import Go
from .java import Java
from .javascript import JavaScript
from .julia import Julia
from .python import Python
from .ruby import Ruby
from .rust import Rust
from .typescript import TypeScript


DEFAULT_GRAMMARS: dict[str, type[Language]] = {
    ".py":  Python,
    ".java": Java,
    ".cpp": Cpp,
    ".cc":  Cpp,
    ".cxx": Cpp,
    ".hpp": Cpp,
    ".hxx": Cpp,
    ".c":   C,
    ".h":   C,
    ".go":  Go,
    ".rs":  Rust,
    ".js":  JavaScript,
    ".mjs": JavaScript,
    ".cjs": JavaScript,
    ".ts":  TypeScript,
    ".tsx": TypeScript,
    ".rb":  Ruby,
    ".jl":  Julia,
    ".cs":  CSharp,
}


# Reverse lookup: language id (the string stored on ParseResult.language
# and exposed via Structure.language_for) → grammar class. Used by view
# methods that need the grammar's control-flow vocabulary without
# threading the class through every record.
LANGUAGE_BY_ID: dict[str, type[Language]] = {
    cls.id: cls
    for cls in (C, Cpp, CSharp, Go, Java, JavaScript, Julia, Python, Ruby, Rust, TypeScript)
}


__all__ = [
    "C", "Cpp", "CSharp", "Go", "Java", "JavaScript",
    "Julia", "Python", "Ruby", "Rust", "TypeScript",
    "DEFAULT_GRAMMARS",
    "LANGUAGE_BY_ID",
]
