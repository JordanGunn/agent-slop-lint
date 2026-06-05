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


@dataclass(frozen=True)
class ParameterMutation:
    """An in-place mutation of a collection/reference parameter. Legacy: types.hidden_mutators."""

    parameter: str
    kind: str       # deref-assign / field-assign / subscript-assign / collection-method
    line: int


@dataclass(frozen=True)
class SentinelParameter:
    """A stringly-typed parameter with a sentinel name. Legacy: types.sentinels.

    ``observed_literals`` are the call-site strings that flowed into it, the
    evidence it should be a Literal/Enum.
    """

    name: str
    observed_literals: tuple[str, ...]


# --- Class altitude (Chidamber-Kemerer 1994) --------------------------------

@dataclass(frozen=True)
class CKMetrics:
    """The CK suite for one class. Legacy: coupling, inheritance.depth,
    inheritance.children (+ complexity.cyclomatic at class scope).

    WMC is intentionally absent as a field: it is Sigma of method weights with
    the weight unspecified by CK, so it equals ``cyclomatic()`` under cyclomatic
    weight and ``nom`` under unit weight. Both are already reachable; a wmc
    field would duplicate one of them. ``lcom`` is not in the legacy — carried
    as intended future behaviour.
    """

    nom: int        # number of methods (WMC under unit weight)
    dit: int        # depth of inheritance tree
    noc: int        # number of children
    cbo: int        # coupling between objects
    lcom: int | None  # lack of cohesion in methods — future

    def as_dict(self) -> dict[str, Any]:
        return {"nom": self.nom, "dit": self.dit, "noc": self.noc,
                "cbo": self.cbo, "lcom": self.lcom}

    def narrate(self, *, cbo_floor: int, dit_floor: int, noc_floor: int) -> str:
        """Claim-free prose over the CK profile, naming only the metrics past their
        attention-floor. Descriptive, never a verdict — the floors mark "worth a
        look", not "defect". NOC in particular is framed as ambiguous: a broad base
        is frequently a healthy abstraction, not a god-base.
        """
        parts: list[str] = []
        if self.cbo > cbo_floor:
            parts.append(
                f"couples to {self.cbo} other classes (high — typical ≤ {cbo_floor}; "
                f"resists isolated testing and change)"
            )
        if self.dit > dit_floor:
            parts.append(
                f"inheritance depth {self.dit} (deep — typical ≤ {dit_floor}; many "
                f"inherited behaviours to reason about)"
            )
        if self.noc > noc_floor:
            parts.append(
                f"{self.noc} direct subclasses (broad base — often a healthy "
                f"abstraction, but worth confirming it is not a god-base)"
            )
        if not parts:
            return f"CK profile within typical bounds ({self.nom} methods)."
        return f"CK profile — {'; '.join(parts)}. ({self.nom} methods.)"


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
class RedundancyPair:
    """Two sibling callables sharing non-trivial callees. Legacy: redundancy."""

    left: str
    right: str
    shared_callees: tuple[str, ...]


@dataclass(frozen=True)
class CloneCluster:
    """Type-2 clone cluster (identical AST leaf-type fingerprint). Legacy: duplication."""

    members: tuple[str, ...]
    leaf_count: int
    #: Narrowest scope containing all clone members (module if co-located, else
    #: package/realm) — the attribution target. ``None`` if unresolvable.
    locus: ScopeId | None = None


@dataclass(frozen=True)
class CallIsland:
    """One connected component of a module's intra-file call graph. Legacy: lexical.confusion."""

    members: tuple[str, ...]


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
