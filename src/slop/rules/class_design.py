"""class-coupling, class-inheritance-depth, class-children, class-cohesion: the Chidamber and
Kemerer (1994) class measures, plus cohesion, as limits at the class altitude.

- ``class-coupling``: CBO, the number of other classes this one depends on.
- ``class-inheritance-depth``: DIT, the length of the longest path up its base classes.
- ``class-children``: NOC, the number of classes that inherit from it directly.
- ``class-cohesion``: LCOM4 (Hitz and Montazeri 1995), the number of groups of methods
  joined through shared instance members. Off by default: its precision on real code has
  not been measured, and a class of independent accessors reads as many groups.

The numbers come from ``Structure.over(cls)``; ``slop shape`` prints the same ones.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class CouplingRule(Limit):
    name = "class-coupling"
    description = "a class depends on more other classes (CBO) than the limit"
    altitude = ScopeKind.CLASS
    default_limit = 8

    def measure(self, view: Structure) -> int:
        return view.cbo()

    def describe(self, scope: Scope, value: int, limit: float, view: Structure) -> str:
        return f"{scope.qualname} is coupled to {value} other classes (limit {limit})"


class InheritanceDepthRule(Limit):
    name = "class-inheritance-depth"
    description = "a class sits deeper in an inheritance tree (DIT) than the limit"
    altitude = ScopeKind.CLASS
    default_limit = 4

    def measure(self, view: Structure) -> int:
        return view.dit()

    def describe(self, scope: Scope, value: int, limit: float, view: Structure) -> str:
        return f"{scope.qualname} has inheritance depth {value} (limit {limit})"


class ChildrenRule(Limit):
    name = "class-children"
    description = "a class has more direct subclasses (NOC) than the limit"
    altitude = ScopeKind.CLASS
    default_limit = 10

    def measure(self, view: Structure) -> int:
        return view.noc()

    def describe(self, scope: Scope, value: int, limit: float, view: Structure) -> str:
        return f"{scope.qualname} has {value} direct subclasses (limit {limit})"


class CohesionRule(Limit):
    name = "class-cohesion"
    description = "a class's methods fall into more groups sharing no instance member (LCOM4) than the limit"
    altitude = ScopeKind.CLASS
    default_limit = 1
    # Accessors are left out of the groups (slop.ast.accessor). Measured 2026-11-12, that removed
    # 6 of 20 warnings on slop and laszy, every one a class split only by getters; the rest are
    # mostly records with two independent views, which only judgement can tell from two jobs.
    subjective = True

    def measure(self, view: Structure) -> int | None:
        cohesion = view.cohesion()
        return None if cohesion is None else cohesion.lcom4

    def describe(self, scope: Scope, value: int, limit: float, view: Structure) -> str:
        groups = "; ".join("{" + ", ".join(g) + "}" for g in view.cohesion().groups)
        return (f"{scope.qualname} has {value} method groups sharing no instance member "
                f"(limit {limit}): {groups}")
