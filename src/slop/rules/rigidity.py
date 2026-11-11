"""rigid-package: a package in Martin's Zone of Pain.

Defined at the package altitude. A package is rigid when it is both stable (many
dependents, low instability I) and concrete (few abstractions, low abstractness A):
callers are tied to it and there is nothing to substitute through. Martin (1994) puts
such a package far from the main sequence A + I = 1, so the normalised distance
D' = |A + I - 1| is large. Zone membership (I < 0.3 and A < 0.3) comes from the metric;
the rule adds a limit on D' so only packages deep in the corner are reported.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class RigidityRule(Limit):
    name = "rigid-package"
    description = "a package is stable and concrete, far from Martin's main sequence"
    altitude = ScopeKind.PACKAGE
    default_limit = 0.7
    subjective = True       # stable and concrete only hurts if the package changes, which D' cannot see

    def measure(self, view: Structure) -> float | None:
        return view.martin_metrics().distance if view.in_zone_of_pain() else None

    def describe(self, component: Scope, value: float, limit: float, view: Structure) -> str:
        m = view.martin_metrics()
        return (f"{component.qualname} is in the Zone of Pain: distance {value:.2f} "
                f"(limit {limit}), instability {m.instability:.2f}, abstractness {m.abstractness:.2f}")
