"""useless-package: a package in Martin's Zone of Uselessness.

Defined at the package altitude. A package is useless when it is both unstable (few or no
dependents, high instability I) and abstract (heavy on interfaces, high abstractness A):
the abstractions exist but almost nothing depends on them. Martin (1994) puts such a
package in the corner opposite the Zone of Pain, so D' = |A + I - 1| is again large. Zone
membership (I > 0.7 and A > 0.7) comes from the metric; the rule adds a limit on D'.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from .main_sequence import Zone


class UselessnessRule(Zone):
    name = "useless-package"
    description = "a package is unstable and abstract, far from Martin's main sequence"
    zone = "Uselessness"

    def in_zone(self, view: Structure) -> bool:
        return view.in_zone_of_uselessness()
