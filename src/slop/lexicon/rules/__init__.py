"""Lexical rule registry.

Naming-discipline rules that ride on the ``Lexicon`` view: stutter,
verbosity, cowards, hammers, tautology, sprawl, imposters, slackers,
confusion. Each rule points at structural debt expressed through
naming.
"""
from __future__ import annotations

from slop.linter.types import RuleDefinition

from .confusion import run_confusion
from .cowards import run_cowards
from .hammers import run_hammers
from .imposters import run_imposters
from .slackers import run_slackers
from .sprawl import run_sprawl
from .stutter import run_stutter
from .tautology import run_tautology
from .verbosity import run_verbosity

LEXICAL_RULES: list[RuleDefinition] = [
    RuleDefinition(
        name="lexical.stutter",
        category="lexical.stutter",
        description="Names repeating tokens from any enclosing scope (package/module/class/function)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 2 tokens",
        run=run_stutter,
    ),
    RuleDefinition(
        name="lexical.verbosity",
        category="lexical.verbosity",
        description="Function/class names with too many word-tokens (missing namespace)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 3 tokens",
        run=run_verbosity,
    ),
    RuleDefinition(
        name="lexical.cowards",
        category="lexical.cowards",
        description="Identifiers ending in disambiguator suffixes (_1, _v2, _old, _new, _local) — provenance collapse",
        default_severity="warning",
        default_enabled=True,
        threshold_label="any match",
        run=run_cowards,
    ),
    RuleDefinition(
        name="lexical.hammers",
        category="lexical.hammers",
        description="Catchall vocabulary (Manager, Helper, Util, Spec) — one word for every nail",
        default_severity="warning",
        default_enabled=True,
        threshold_label="banlist match",
        run=run_hammers,
    ),
    RuleDefinition(
        name="lexical.tautology",
        category="lexical.tautology",
        description="Identifier suffixes that tautologically restate type annotations (_dict, _path, _str)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="suffix matches type",
        run=run_tautology,
    ),
    RuleDefinition(
        name="lexical.sprawl",
        category="lexical.sprawl",
        description="Closed alphabet sprawls across naming templates (Wille 1982 FCA)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 3 alphabet × ≥ 2 ops",
        run=run_sprawl,
    ),
    RuleDefinition(
        name="lexical.imposters",
        category="lexical.imposters",
        description="Parameters camouflaged as ordinary deps; missing receiver class",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 3 functions sharing param",
        run=run_imposters,
    ),
    RuleDefinition(
        name="lexical.slackers",
        category="lexical.slackers",
        description="Sibling functions sharing input but refusing to align by naming template",
        default_severity="warning",
        default_enabled=True,
        threshold_label="< 30% template coverage",
        run=run_slackers,
    ),
    RuleDefinition(
        name="lexical.confusion",
        category="lexical.confusion",
        description="File holds multiple distinct strong-receiver clusters (Lanza & Marinescu Extract Class)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 2 strong receivers in one file",
        run=run_confusion,
    ),
]
