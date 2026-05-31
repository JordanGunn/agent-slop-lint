"""Concrete grammars + registry. Broadening from Python outward."""
from __future__ import annotations

from .c import C
from .go import Go
from .julia import Julia
from .python import Python

# language id -> Grammar class
GRAMMARS_BY_ID: dict[str, type] = {
    Python.id: Python,
    Go.id: Go,
    C.id: C,
    Julia.id: Julia,
}

__all__ = ["Python", "Go", "C", "Julia", "GRAMMARS_BY_ID"]
