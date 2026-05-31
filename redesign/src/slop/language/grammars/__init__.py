"""Concrete grammars + registry. Broadening from Python outward."""
from __future__ import annotations

from .c import C
from .csharp import CSharp
from .go import Go
from .java import Java
from .julia import Julia
from .python import Python

# language id -> Grammar class
GRAMMARS_BY_ID: dict[str, type] = {
    Python.id: Python,
    Go.id: Go,
    C.id: C,
    Julia.id: Julia,
    Java.id: Java,
    CSharp.id: CSharp,
}

__all__ = ["Python", "Go", "C", "Julia", "Java", "CSharp", "GRAMMARS_BY_ID"]
