"""useless-package: a package in Martin's Zone of Uselessness.

Defined at the package altitude. A package is useless when it is both unstable (few or no
dependents, high instability I) and abstract (heavy on interfaces, high abstractness A):
the abstractions exist but almost nothing depends on them. Martin (1994) puts such a
package in the corner opposite the Zone of Pain, so D' = |A + I - 1| is again large. Zone
membership (I > 0.7 and A > 0.7) comes from the metric; the rule adds a limit on D'.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class UselessnessRule(Limit):
    name = "useless-package"
    description = "a package is unstable and abstract, far from Martin's main sequence"
    altitude = ScopeKind.PACKAGE
    default_limit = 0.7
    subjective = True       # as rigid-package: the metric has no notion of how often a package changes

    def measure(self, view: Structure) -> float | None:
        return view.martin_metrics().distance if view.in_zone_of_uselessness() else None

    def describe(self, component: Scope, value: float, limit: float, view: Structure) -> str:
        m = view.martin_metrics()
        return (f"{component.qualname} is in the Zone of Uselessness: distance {value:.2f} "
                f"(limit {limit}), instability {m.instability:.2f}, abstractness {m.abstractness:.2f}")
