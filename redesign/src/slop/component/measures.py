"""Metric capability interfaces — the inventory, expressed as ABCs.

This module is the durable ledger. Every metric the legacy ``slop`` computes has
a method signature here, grouped by the altitude that owns it and whether it
aggregates. Signatures exist even where the computation is not yet ported, so
the long tail cannot be silently dropped while porting the high-value few.

Two placement classes:

- **Aggregatable** (``ComplexityMeasures``): defined at the Callable leaf,
  answerable at every altitude above by summation. Mixed into ``Component`` so
  every component answers them.
- **Position-unique**: defined at exactly one kind. Mixed only into that kind.

Return types are provisional where the legacy shape is not yet pinned; params
may be incomplete. Completeness of the *surface* is the contract, not finality
of the signatures.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .metrics import (
    CallIsland,
    CKMetrics,
    CloneCluster,
    DependencyCycle,
    HalsteadProfile,
    Hotspot,
    MagicLiteral,
    Orphan,
    PackageMetrics,
    ParameterMutation,
    RedundancyPair,
    SentinelParameter,
)


class ComplexityMeasures(ABC):
    """Aggregatable scalar complexity. Defined on the Callable leaf as the
    primitive; on every container as the sum over its callables.

    ``class.cyclomatic()`` is Sigma over methods; ``module.cyclomatic()`` is
    Sigma over functions + classes; and so on up to Corpus. This is *not* WMC —
    WMC is a distinct Class metric (see ``ClassMeasures``).

    Legacy: complexity.cyclomatic / .cognitive / .combinatorial / .volume,
    structure/complexity.py + structure/halstead.py.
    """

    @abstractmethod
    def cyclomatic(self) -> int:
        """McCabe (1976) CCN — primitive at Callable, summed upward."""
        ...

    @abstractmethod
    def cognitive(self) -> int:
        """Campbell (2018) cognitive complexity — primitive at Callable, summed upward."""
        ...

    @abstractmethod
    def combinatorial(self) -> int:
        """Nejmeh (1988) NPATH — multiplicative within a callable, summed across callables."""
        ...

    @abstractmethod
    def volume(self) -> float:
        """Halstead (1977) volume V = N.log2(eta) — summable component of the profile."""
        ...

    @abstractmethod
    def sloc(self) -> int:
        """Source lines of code (non-blank, non-comment) — summed upward."""
        ...


class CallableMeasures(ABC):
    """Callable-only measures that do not aggregate.

    Legacy: complexity.density (non-additive), types.magic_literals,
    types.hidden_mutators, types.sentinels.
    """

    @abstractmethod
    def halstead(self) -> HalsteadProfile:
        """Full Halstead profile; only ``volume`` aggregates (see ComplexityMeasures)."""
        ...

    @abstractmethod
    def halstead_density(self) -> float:
        """Halstead difficulty D = (eta1/2).(N2/eta2). Non-additive — Callable only."""
        ...

    @abstractmethod
    def magic_literals(self) -> Sequence[MagicLiteral]:
        """Distinct non-trivial numeric literals in the body."""
        ...

    @abstractmethod
    def mutated_parameters(self) -> Sequence[ParameterMutation]:
        """Collection/reference parameters mutated in place."""
        ...

    @abstractmethod
    def sentinel_parameters(self) -> Sequence[SentinelParameter]:
        """Stringly-typed parameters with sentinel names that want Literal/Enum."""
        ...


class ClassMeasures(ABC):
    """Chidamber-Kemerer (1994) suite — defined only where a Class exists.

    Legacy: complexity.cyclomatic(class), coupling, inheritance.depth,
    inheritance.children, structure/class_index.py. ``lcom`` is not in the
    legacy; carried as intended future behaviour.

    No ``wmc()`` here, deliberately. CK define WMC = Sigma of method *weights*
    with the weight unspecified: weight=cyclomatic makes WMC identical to the
    aggregatable ``cyclomatic()`` at class scope, and weight=1 makes it
    ``method_count()`` (NOM). WMC is therefore a weighting family over metrics
    we already expose, not a metric of its own — exposing a third ``wmc()``
    would just duplicate ``cyclomatic()`` and invite drift.
    """

    @abstractmethod
    def ck(self) -> CKMetrics:
        """The full CK record (nom/dit/noc/cbo/lcom) in one call. WMC under
        cyclomatic weight is ``cyclomatic()``; under unit weight, ``method_count()``."""
        ...

    @abstractmethod
    def method_count(self) -> int:
        """NOM — number of methods. (WMC under unit weight, CK's other anchor.)"""
        ...

    @abstractmethod
    def dit(self) -> int:
        """Depth of Inheritance Tree (known parents only)."""
        ...

    @abstractmethod
    def noc(self) -> int:
        """Number of Children (direct, corpus-local subclasses)."""
        ...

    @abstractmethod
    def cbo(self) -> int:
        """Coupling Between Objects — distinct outbound class references."""
        ...

    @abstractmethod
    def lcom(self) -> int | None:
        """Lack of Cohesion in Methods. Returns None until ported (future)."""
        ...


class ModuleMeasures(ABC):
    """Module-only structural and relational measures.

    Legacy: god_module, types.escape_hatches, redundancy, duplication,
    lexical.confusion (call-islands), structure/redundancy.py + clones.py.

    Note ``call_islands`` is the *structural* grab-bag detector (who-calls-whom
    fragmentation) the legacy mislabelled ``lexical.confusion``. The lexical
    sense of confusion — one namespace holding too many distinct concepts —
    is a separate, scope-polymorphic Lexicon measurement, not this.
    """

    @abstractmethod
    def definition_count(self) -> int:
        """Top-level callable + class-like definitions (god-module size)."""
        ...

    @abstractmethod
    def escape_hatch_density(self) -> float:
        """Fraction of type annotations using escape-hatch types (Any, interface{}, ...)."""
        ...

    @abstractmethod
    def redundant_siblings(self) -> Sequence[RedundancyPair]:
        """Sibling callables sharing non-trivial callees (missing-helper signal)."""
        ...

    @abstractmethod
    def call_islands(self) -> Sequence[CallIsland]:
        """Disjoint components of the intra-module call graph among sibling
        callables (structural grab-bag topology). The honest renaming of legacy
        ``lexical.confusion``; structural and module-scoped — distinct from
        lexical concept-dispersion."""
        ...

    @abstractmethod
    def clone_clusters(self) -> Sequence[CloneCluster]:
        """Type-2 clone clusters among this module's callables."""
        ...


class PackageMeasures(ABC):
    """Robert C. Martin (1994) package measures — defined only at Package.

    Legacy: rigidity, uselessness, structure/packages.py + architecture.py.
    """

    @abstractmethod
    def martin_metrics(self) -> PackageMetrics:
        """Ca/Ce/I/A/D' for this package."""
        ...

    @abstractmethod
    def in_zone_of_pain(self) -> bool:
        """Rigidity: I<0.3 AND A<0.3 — stable and concrete."""
        ...

    @abstractmethod
    def in_zone_of_uselessness(self) -> bool:
        """I>0.7 AND A>0.7 — unstable and abstract."""
        ...

    @abstractmethod
    def is_runt(self) -> bool:
        """One module + trivial __init__ — boundary does not earn its weight.
        Legacy: lexical.runts."""
        ...


class CorpusMeasures(ABC):
    """Analysis-wide measures that span realms/packages/modules.

    Legacy: orphans, duplication (cross-module), hotspots.
    """

    @abstractmethod
    def orphans(self) -> Sequence[Orphan]:
        """Unreferenced top-level symbols across the analysis surface (advisory)."""
        ...

    @abstractmethod
    def duplication(self) -> Sequence[CloneCluster]:
        """Type-2 clone clusters across the whole corpus."""
        ...

    @abstractmethod
    def hotspots(self) -> Sequence[Hotspot]:
        """Churn-weighted complexity per file (needs git history)."""
        ...

    @abstractmethod
    def dependency_cycles(self) -> Sequence[DependencyCycle]:
        """Import cycles (Tarjan SCC) across the corpus. See also DependencyGraph."""
        ...
