"""Result-record dataclasses for cross-cutting Structure view methods.

The compute methods on ``Structure`` that need external systems —
``hotspots`` (git history) and ``orphans`` (cross-file references via
ripgrep) — return rich records that the rule layer translates into
``Slop`` findings. Frozen dataclasses; structural rules consume them
read-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Import:
    """A single import / include / require edge extracted from a file.

    ``module`` is the raw string from the import statement (e.g.
    ``"foo.bar"``, ``"./util"``, ``"stdio.h"``); resolution to an
    absolute file path is a separate step on the dependency graph.
    """

    file: str       # absolute path of the importing file
    module: str     # raw module string from the import statement
    kind: str       # grammar-specific label: "import" | "from_import" |
                    # "esm" | "go_import" | "java_import" | "csharp_using" |
                    # "include_local" | "include_system" | "ruby_require" |
                    # "use" | etc.
    line: int       # 1-based source line


@dataclass(frozen=True)
class HiddenMutation:
    """One detected mutation event on a parameter."""

    param_name: str
    method: str
    line: int


@dataclass(frozen=True)
class HiddenMutator:
    """A function found to mutate one or more parameters in place.

    ``mutations`` is the ordered list of mutation events. ``mutation_count``
    is convenience — equals ``len(mutations)``.
    """

    file: str
    function_name: str
    line: int
    end_line: int
    language: str
    mutations: tuple[HiddenMutation, ...]

    @property
    def mutation_count(self) -> int:
        return len(self.mutations)


@dataclass(frozen=True)
class SentinelParameter:
    """A stringly-typed parameter candidate.

    ``annotated`` is True when the parameter has an explicit
    string-typed annotation (Python ``str``, C ``char *``,
    C++ ``std::string``); False for dynamically-typed languages
    (Ruby) and for Python params with no annotation. Call-site
    enrichment populates ``call_site_literals`` (the distinct string
    constants observed at call sites) for the languages where the
    substrate can find them.
    """

    file: str
    function_name: str
    param_name: str
    param_line: int
    language: str
    annotated: bool
    call_site_literals: tuple[str, ...] = field(default_factory=tuple)
    call_site_count: int = 0


@dataclass(frozen=True)
class RedundancyPair:
    """Two sibling top-level callables with overlapping callee sets.

    ``score = |shared| / max(|callees_a|, |callees_b|)``. Both fn_a
    and fn_b live in the same file; the rule reports the pair as one
    finding anchored on fn_a's location.
    """

    file: str
    fn_a: str
    fn_b: str
    fn_a_line: int
    fn_b_line: int
    shared_callees: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class CloneMember:
    """One callable that belongs to a Type-2 clone cluster.

    ``file`` is the absolute file path (callers may normalise to
    relative for display). ``line`` is the 1-based start line.
    """

    file: str
    name: str
    line: int
    end_line: int
    language: str
    fingerprint: str


@dataclass(frozen=True)
class CloneCluster:
    """A group of callables sharing the same AST leaf-type fingerprint.

    ``size`` is len(members). Clusters with size == 1 are not emitted —
    a clone needs at least one peer.
    """

    fingerprint: str
    size: int
    members: tuple[CloneMember, ...]


@dataclass(frozen=True)
class CloneReport:
    """Output of ``Structure.clones`` — clusters + corpus-level summary."""

    clusters: tuple[CloneCluster, ...]
    functions_analyzed: int
    clone_fraction: float       # cloned-functions / total-functions


@dataclass(frozen=True)
class PackageMetrics:
    """Robert C. Martin (1994) package architecture metrics for one package.

    The distance from the main sequence ``D' = |A + I - 1|`` measures how
    far a package is from the line connecting Zone of Pain (I=0, A=0,
    stable + concrete) to Zone of Uselessness (I=1, A=1, unstable +
    abstract). Both endpoints are equally far off — D'=1 is maximum
    drift; D'=0 is on the line.

    ``ca``/``ce`` are package-level afferent / efferent coupling counts;
    ``na``/``nc`` are per-package counts of abstract / concrete types as
    classified by ``Language.is_abstract_scope``.
    """

    name: str
    language: str
    files: tuple[str, ...]
    ca: int                            # afferent coupling
    ce: int                            # efferent coupling
    na: int                            # abstract type count
    nc: int                            # concrete type count
    instability: float | None          # I = Ce / (Ca + Ce)
    abstractness: float | None         # A = Na / (Na + Nc)
    distance: float | None             # D' = |A + I - 1|
    zone: str                          # "pain" | "uselessness" | "warning" |
                                       # "clean" | "ok" | "unknown"


@dataclass(frozen=True)
class DependencyGraph:
    """Resolved file→file import graph.

    ``efferent[f]`` is the set of files that ``f`` imports (outbound
    edges). ``afferent[f]`` is the reverse — files that import ``f``.
    Unresolved imports (module strings that don't map to any file in
    the corpus) are dropped at this layer; they remain visible in the
    raw ``Structure.imports()`` output.
    """

    efferent: dict[str, frozenset[str]]
    afferent: dict[str, frozenset[str]]


@dataclass(frozen=True)
class FileHotspot:
    """Per-file growth-weighted complexity record (Tornhill 2015).

    Score = ``sum_ccx × max(0, loc_delta)``. Files are classified into
    quadrants by 75th-percentile cutoffs on the sum_ccx and loc_delta
    axes; when the corpus has fewer than 8 ranked files the classifier
    abstains and emits ``insufficient_data``.
    """

    file: str                           # repo-root-relative, forward-slash
    path: str                           # absolute filesystem path
    language: str
    sum_ccx: int                        # Σ cyclomatic over callables in file
    max_ccx: int                        # worst single callable in file
    loc_delta: int                      # net (insertions - deletions) in window
    loc_insertions: int
    loc_deletions: int
    commit_count: int
    first_seen: str                     # ISO date, oldest commit in window
    last_seen: str                      # ISO date, newest commit in window
    hotspot_score: float
    quadrant: str                       # "hotspot" | "stable_complex" |
                                        # "churning_simple" | "calm" |
                                        # "insufficient_data"


@dataclass(frozen=True)
class OrphanCandidate:
    """Dead-code candidate — a symbol with zero detected external references.

    Confidence is heuristic (length, common-name list, dynamic-language
    risk); the advisory wording is enforced by the rule layer. Static
    analysis can't see reflection / dynamic dispatch / plugin
    registration / cross-language calls, so every candidate needs human
    verification regardless of confidence.
    """

    symbol: str
    symbol_type: str        # "function" | "class" | etc.
    file: str               # absolute path of the definition file
    line: int               # definition line (1-based; 0 if unknown)
    external_refs: int      # references outside the definition file
    confidence: str         # "high" | "medium" | "low"
    caveats: tuple[str, ...] = field(default_factory=tuple)
