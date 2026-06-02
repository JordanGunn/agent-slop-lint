"""Scope data records — value types the scope model owns.

Frozen value records that are structural *facts* about scopes, distinct from the
metric *results* in ``metrics/structural/records.py``. ``ImportDecl`` is a module's
raw, pre-resolution import — a property of the Module (returned by
``Module.imports()``), consumed downward by the dependency-graph builder.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportDecl:
    """A raw, pre-resolution import on a Module. Resolution against the corpus turns
    it into a ``DependencyEdge``; holding the raw form on the Module keeps the
    unresolved fact addressable."""

    specifier: str   # the raw module string as written
    kind: str        # import | from | include | require | use | ...
    line: int
