"""complexity.cognitive: Campbell (2018) cognitive complexity of a callable.

Defined at the callable altitude. Cognitive complexity weighs how hard a unit is to read
(nesting counts more than a flat sequence of branches), which cyclomatic complexity does
not.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class CognitiveRule(Limit):
    name = "complexity.cognitive"
    description = "a callable's cognitive complexity (Campbell 2018) is over the limit"
    altitude = ScopeKind.CALLABLE
    default_limit = 15

    def measure(self, view: Structure) -> int:
        return view.cognitive()

    def describe(self, component: Scope, value: int, limit: float, view: Structure) -> str:
        return f"{component.qualname} has cognitive complexity {value} (limit {int(limit)})"
