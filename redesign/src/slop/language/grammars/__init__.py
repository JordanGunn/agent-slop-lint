"""Concrete grammars + registry. Broadening from Python outward."""
from __future__ import annotations

from .go import Go
from .python import Python

# language id -> Grammar class
GRAMMARS_BY_ID: dict[str, type] = {
    Python.id: Python,
    Go.id: Go,
}

__all__ = ["Python", "Go", "GRAMMARS_BY_ID"]
