"""Zone: a package that sits far from Martin's main sequence A + I = 1 inside one corner.

Martin (1994) measures a package's instability I (efferent over total coupling) and its
abstractness A, and the distance D' = |A + I - 1| from the line where they balance. The
two corners are the Zone of Pain (stable and concrete) and the Zone of Uselessness
(unstable and abstract). Zone membership comes from the metric; a subclass names its zone
and says whether a package is in it, and the rule adds a limit on D'.
"""
from __future__ import annotations

from typing import ClassVar

from ..metrics.structural.view import Structure
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class Zone(Limit):
    altitude = ScopeKind.PACKAGE
    default_limit = 0.7
    subjective = True       # stable and concrete (or unstable and abstract) only hurts if the package changes, which D' cannot see
    zone: ClassVar[str]

    def in_zone(self, view: Structure) -> bool:
        raise NotImplementedError

    def measure(self, view: Structure) -> float | None:
        return view.martin_metrics().distance if self.in_zone(view) else None

    def describe(self, scope: Scope, value: float, limit: float, view: Structure) -> str:
        m = view.martin_metrics()
        return (f"{scope.qualname} is in the Zone of {self.zone}: distance {value:.2f} "
                f"(limit {limit}), instability {m.instability:.2f}, abstractness {m.abstractness:.2f}")
