"""Concrete grammars + registry — all 11 languages."""
from __future__ import annotations

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

_GRAMMARS = [Python, Go, C, Cpp, Julia, Java, CSharp, Rust, Ruby, JavaScript, TypeScript]

# language id -> Grammar class
GRAMMARS_BY_ID: dict[str, type] = {g.id: g for g in _GRAMMARS}

__all__ = [
    "Python", "Go", "C", "Cpp", "Julia", "Java", "CSharp", "Rust", "Ruby",
    "JavaScript", "TypeScript", "GRAMMARS_BY_ID",
]
