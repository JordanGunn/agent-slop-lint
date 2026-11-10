"""Value records returned by metric methods.

These are data contracts (frozen records), not computations. They fix the shape
a metric reports; the computation that fills them is built per altitude during
rule porting (build step 5). Fields known from the legacy inventory are declared
now; provisional records carry the fields we already know we want and may grow.

Each record cites the legacy rule/compute it preserves, so the inventory is
traceable from the new model back to the source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...identity import ScopeId


# --- Complexity primitives (Callable altitude) ------------------------------

@dataclass(frozen=True)
class HalsteadProfile:
    """Halstead (1977) software-science measures for one callable.

    Legacy: complexity.volume / complexity.density, structure/halstead.py.
    ``n1``/``n2`` distinct operators/operands; ``N1``/``N2`` total occurrences.
    ``volume`` aggregates upward; ``difficulty``/``effort`` are non-additive.
    """

    n1: int
    n2: int
    N1: int
    N2: int
    volume: float
    difficulty: float
    effort: float


@dataclass(frozen=True)
class MagicLiteral:
    """A non-trivial numeric literal in a callable body. Legacy: types.magic_literals."""

    value: str
    line: int


# --- Class altitude (Chidamber-Kemerer 1994) --------------------------------

@dataclass(frozen=True)
class Cohesion:
    """How a class's methods share instance members (LCOM4, Hitz and Montazeri 1995).

    ``groups`` are the sets of methods joined through shared members, in declaration order;
    ``len(groups)`` is LCOM4 (1 = cohesive). ``detached`` are methods that reach no instance
    member and are reached by none, so they have no state to be cohesive about. An LCOM4 of
    0 means nothing was measurable (no instance methods, or every one detached), not a
    perfectly cohesive class."""

    groups: tuple[tuple[str, ...], ...]
    detached: tuple[str, ...]

    @property
    def lcom4(self) -> int:
        return len(self.groups)

    def as_dict(self) -> dict[str, Any]:
        return {"lcom4": self.lcom4, "method_groups": [list(g) for g in self.groups],
                "detached": list(self.detached)}


@dataclass(frozen=True)
class CKMetrics:
    """The CK suite for one class. Legacy: coupling, inheritance.depth,
    inheritance.children (+ complexity.cyclomatic at class scope).

    WMC is intentionally absent as a field: it is Sigma of method weights with
    the weight unspecified by CK, so it equals ``cyclomatic()`` under cyclomatic
    weight and ``nom`` under unit weight. Both are already reachable; a wmc
    field would duplicate one of them. Cohesion is LCOM4 (Hitz and Montazeri 1995), not
    CK's original pairwise LCOM: ``cohesion`` counts the groups of methods joined through shared
    instance members and names them.
    """

    nom: int        # number of methods (WMC under unit weight)
    dit: int        # depth of inheritance tree
    noc: int        # number of children
    cbo: int        # coupling between objects
    #: ``None`` when the language's instance member access cannot be read from syntax
    #: (Java, C#, C++), which is not the same as a class with no groups.
    cohesion: Cohesion | None
    #: Reasons the inheritance numbers may not be exact (a class that shares its name with
    #: another, or an unresolvable base name). Empty when the numbers are exact.
    caveats: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"nom": self.nom, "dit": self.dit, "noc": self.noc, "cbo": self.cbo,
                "lcom4": None if self.cohesion is None else self.cohesion.lcom4,
                "method_groups": None if self.cohesion is None
                else [list(g) for g in self.cohesion.groups],
                "detached": None if self.cohesion is None else list(self.cohesion.detached),
                "caveats": list(self.caveats)}

    @property
    def lcom4(self) -> int | None:
        return None if self.cohesion is None else self.cohesion.lcom4


# --- Package altitude (Robert C. Martin 1994) -------------------------------

@dataclass(frozen=True)
class PackageMetrics:
    """Martin (1994) package stability/abstractness. Legacy: rigidity, uselessness,
    structure/packages.py. Defined only at the Package altitude.
    """

    afferent: int       # Ca — incoming dependencies
    efferent: int       # Ce — outgoing dependencies
    instability: float  # I = Ce / (Ca + Ce)
    abstractness: float  # A = abstract types / total types
    distance: float     # D' = |A + I - 1|


# --- Relational / analysis-wide findings ------------------------------------

@dataclass(frozen=True)
class CloneMember:
    """One callable in a clone cluster: its identity (which file it is in), its dotted name
    and its 1-based line. The name alone does not say which of two same-named modules it
    is in."""

    scope: ScopeId
    qualname: str
    line: int


@dataclass(frozen=True)
class CloneCluster:
    """Type-2 clone cluster (identical AST leaf-type fingerprint). Legacy: duplication."""

    members: tuple[CloneMember, ...]
    leaf_count: int
    #: Narrowest scope containing all clone members (module if co-located, else
    #: package/realm) — the attribution target. ``None`` if unresolvable.
    locus: ScopeId | None = None


@dataclass(frozen=True)
class Orphan:
    """An unreferenced top-level symbol (advisory). Legacy: orphans."""

    qualname: str
    kind: str
    confidence: str
    #: The orphaned symbol's own ScopeId — the attribution target. ``None`` if unresolvable.
    locus: ScopeId | None = None
    #: 1-based definition line of the orphaned symbol (0 if unknown).
    line: int = 0


@dataclass(frozen=True)
class Hotspot:
    """Churn x complexity for one file (Tornhill 2015). Legacy: hotspots."""

    path: str
    churn: int
    complexity: int
    quadrant: str
    #: The Module ScopeId for ``path`` — the attribution target. ``None`` if unresolvable.
    locus: ScopeId | None = None
