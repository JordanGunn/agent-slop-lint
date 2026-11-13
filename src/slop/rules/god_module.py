"""god-module: a module declaring too many top-level definitions.

Defined at the module altitude. The measure is a count of breadth, not of depth: the
module's direct class and callable children. Methods inside classes do not count (that is
a class-size question) and neither do lambdas (inline values, not definitions).
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class GodModuleRule(Limit):
    name = "god-module"
    description = "a module declares more top-level definitions than the limit"
    altitude = ScopeKind.MODULE
    default_limit = 20

    def measure(self, view: Structure) -> int:
        return view.definition_count()

    def describe(self, scope: Scope, value: int, limit: float, view: Structure) -> str:
        return f"{scope.qualname} declares {value} top-level definitions (limit {limit})"
