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
