"""halstead-volume: Halstead (1977) volume of a callable.

Volume is the length of the body in operator and operand occurrences, weighted by the
size of its vocabulary: N * log2(n). It reads size and density, so it reports long
straight-line code that has no branches for cyclomatic or cognitive complexity to count.
The default limit of 1000 is the default of the DCM tool; Halstead gave none.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class HalsteadVolumeRule(Limit):
    name = "halstead-volume"
    description = "a callable's Halstead volume (Halstead 1977) is over the limit"
    altitude = ScopeKind.CALLABLE
    default_limit = 1000

    def measure(self, view: Structure) -> float:
        return round(view.volume(), 1)

    def describe(self, component: Scope, value: float, limit: float, view: Structure) -> str:
        return f"{component.qualname} has Halstead volume {value:g} (limit {limit})"
