"""complexity.combinatorial: Nejmeh (1988) NPath, the count of acyclic execution paths.

Defined at the callable altitude. NPath multiplies where cyclomatic complexity adds, so
sequential branches that are harmless to McCabe's measure still blow it up.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class CombinatorialRule(Limit):
    name = "complexity.combinatorial"
    description = "a callable's NPath (Nejmeh 1988) acyclic path count is over the limit"
    altitude = ScopeKind.CALLABLE
    default_limit = 400

    def measure(self, view: Structure) -> int:
        return view.combinatorial()

    def describe(self, component: Scope, value: int, limit: float, view: Structure) -> str:
        return f"{component.qualname} has NPath {value} (limit {int(limit)})"
