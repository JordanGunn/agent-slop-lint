"""Result records returned by ``Lexicon`` view methods.

Lexical rules read these read-only — the view owns the compute, the
record carries pure data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NamedEntity:
    """One named callable or class-like scope, token-split.

    Consumed by lexical rules that reason about entity names
    (verbosity, stutter, cowards, hammers, tautology). ``tokens`` is
    the snake/Camel-split word list; the rule applies its own
    threshold logic on top.
    """

    name: str
    kind: str            # "function" | "class"
    file: str
    line: int
    language: str
    tokens: tuple[str, ...]


@dataclass
class FirstParameterCluster:
    """A group of callables sharing a first parameter, with profile signals.

    Consumed by lexical rules that reason about implicit receivers
    (imposters, slackers, confusion). The cluster is reported at the
    narrowest scope where it coheres; ``verdict`` + ``profile_label``
    classify what the cluster ACTUALLY does (missing class vs
    strategy family vs infrastructure plumbing).
    """

    parameter_name: str
    parameter_types: set[str]
    members: list[tuple[str, str, int]]   # (function_name, file_rel, line)
    verdict: str                           # "strong" | "weak" | "false_positive"
    advisory: str
    scope: str
    scope_kind: str                        # "file" | "package" | "root"
    body_jaccard_mean: float = 0.0
    mean_receiver_calls: float = 0.0
    modal_overlap_mean: float = 0.0
    is_isolate: bool = False
    file_spread: int = 0
    profile_label: str = "unknown"
    # "missing_class" | "dispatch_family" | "strategy_family"
    # | "heterogeneous" | "infrastructure" | "false_positive" | "unknown"
