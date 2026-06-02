"""AnalysisContext — the corpus-global derived state, held at the Corpus root.

Some metrics need cross-scope context a single component cannot carry: CK
(dit/noc/cbo) needs the whole-corpus class hierarchy; Martin's package metrics need
the module dependency graph. These corpus-global artifacts are built once during carve
and held *here*, on the Corpus — not bolted onto individual entity attributes
(hardening B). A region reaches them via ``region.context`` (the owner chain to the
Corpus root); metrics that need them pull from there. New graphs (call graph,
inheritance graph) are added as fields without touching the entities.

Fields are typed loosely on purpose: this is a transport holder, and it will move
into ``scope/`` with the rest of the ownership model — keeping it free of metric/graph
type imports avoids a scope -> metrics/graph coupling at that point.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnalysisContext:
    """Corpus-global derived state. ``None``/empty when not yet built."""

    class_index: Any = None          # the corpus-wide class hierarchy (CK support)
    dep_graph: Any = None            # the module DependencyGraph (Martin / cycles)
    module_pkg: dict = field(default_factory=dict)  # module id -> owning package id
