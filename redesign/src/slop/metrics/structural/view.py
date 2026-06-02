"""Structure — the structural-metric view over a region.

The structural twin of ``lexicon.Lexicon``: the view the rules consume. Constructed
``Structure.over(region)`` (the view layer owns construction; the scope entity grows
no per-view methods). Aggregatable complexity is the primitive at a Callable and the
sum over descendant callables at a container, matching the legacy
``Component.cyclomatic`` aggregate.

Like the rest of ``metrics/structural``, it reads the region's duck-typed surface
(``_ast_node``/``_grammar``/``_iter_callables`` — the same surface ``relational`` uses)
and never imports the concrete scope classes, so ``scope`` can depend on this layer
without a cycle and this layer stays a pure consumer of ``(region, context)``.

Surface is consumer-driven: it carries the metrics a rule actually consumes today
(the aggregatable complexity family + ``call_islands``) and grows as rules are ported.
The full inventory lives in the compute modules beside this one; a new rule adds the
facade method that reaches it.
"""
from __future__ import annotations

from typing import Any

from ...identity import ComponentKind
from . import complexity, halstead
from .relational import call_islands as _call_islands


class Structure:
    """Structural metrics over one region (a scope, or — later — a selection)."""

    def __init__(self, region: Any) -> None:
        self._r = region

    @classmethod
    def over(cls, region: Any) -> "Structure":
        return cls(region)

    # ---- aggregatable complexity: own primitive at a Callable, summed over
    #      descendant callables at a container (each leaf counted once) --------
    def _leaves(self) -> list[Any]:
        r = self._r
        return [r] if r.KIND == ComponentKind.CALLABLE else list(r._iter_callables())

    def cyclomatic(self) -> int:
        return sum(complexity.cyclomatic(c._ast_node(), c._grammar) for c in self._leaves())

    def cognitive(self) -> int:
        return sum(complexity.cognitive(c._ast_node(), c._grammar) for c in self._leaves())

    def combinatorial(self) -> int:
        return sum(complexity.combinatorial(c._ast_node(), c._grammar) for c in self._leaves())

    def volume(self) -> float:
        return float(sum(halstead.volume(c._ast_node(), c._grammar) for c in self._leaves()))

    def sloc(self) -> int:
        return sum(halstead.sloc(c._ast_node()) for c in self._leaves())

    # ---- module-level relational ------------------------------------------
    def call_islands(self):
        """Disjoint components of the module's intra-file call graph."""
        return _call_islands(self._r)
