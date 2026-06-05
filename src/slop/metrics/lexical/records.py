"""Value records returned by the lexical view methods. Ported from the legacy
``src/slop/lexicon/records.py``. Data contracts only; the view owns the compute.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...identity import ScopeId


@dataclass(frozen=True)
class NamedEntity:
    """One named callable or class-like scope, token-split. Legacy: lexicon.records.

    Consumed by entity-name rules (verbosity, stutter, hammers). ``tokens`` is the
    snake/Camel-split word list; the rule applies its own threshold on top.

    ``locus`` is the entity's own ``ScopeId`` — the canonical attribution target so a
    finding about this entity lands on the entity, not the corpus the rule dispatched at.
    """

    name: str
    kind: str            # "function" | "class"
    file: str
    line: int
    language: str
    tokens: tuple[str, ...]
    locus: ScopeId


@dataclass
class FirstParameterCluster:
    """A group of callables sharing a first parameter, with profile signals.

    Consumed by implicit-receiver rules (imposters, slackers). The cluster is
    reported at the narrowest scope where it coheres; ``verdict`` + ``profile_label``
    classify what it ACTUALLY does (missing class vs strategy family vs plumbing).
    """

    parameter_name: str
    parameter_types: set[str]
    members: list[tuple[str, str, int]]    # (function_name, file_rel, line)
    verdict: str                            # "strong" | "weak" | "false_positive"
    advisory: str
    scope: str
    scope_kind: str                         # "file" | "package" | "root"
    body_jaccard_mean: float = 0.0
    mean_receiver_calls: float = 0.0
    modal_overlap_mean: float = 0.0
    is_isolate: bool = False
    file_spread: int = 0
    scope_hapax_ratio: float = 0.0
    profile_label: str = "unknown"
    #: Narrowest scope containing all members (the module if co-located, the
    #: package/realm if spread) — the canonical attribution target. ``None`` only
    #: if the members could not be resolved back to the scope tree.
    locus: ScopeId | None = None
