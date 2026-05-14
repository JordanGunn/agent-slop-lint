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
