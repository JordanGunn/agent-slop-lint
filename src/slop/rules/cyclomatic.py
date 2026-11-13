"""cyclomatic-complexity: McCabe (1976) cyclomatic complexity of a callable.

Defined at the callable altitude only. Cyclomatic complexity counts the independent
control-flow paths through one unit. A class-level sum is not that: it grows with the
number of methods, so it measures breadth, and it is left to a class-size rule.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class CyclomaticRule(Limit):
    name = "cyclomatic-complexity"
    description = "a callable's cyclomatic complexity (McCabe 1976) is over the limit"
    altitude = ScopeKind.CALLABLE
    default_limit = 10

    def measure(self, view: Structure) -> int:
        return view.cyclomatic()

    def describe(self, scope: Scope, value: int, limit: float, view: Structure) -> str:
        return f"{scope.qualname} has cyclomatic complexity {value} (limit {limit})"
