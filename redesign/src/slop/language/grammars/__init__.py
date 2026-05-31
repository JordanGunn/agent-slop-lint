"""Concrete grammars + registries. Python-first; others added when broadening."""
from __future__ import annotations

from .python import Python

# language id -> Grammar class
GRAMMARS_BY_ID: dict[str, type] = {
    Python.id: Python,
}

__all__ = ["Python", "GRAMMARS_BY_ID"]
