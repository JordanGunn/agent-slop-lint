"""Structural metric registry — assembles per-module ``RULE`` constants.

Each metric module owns its own ``RULE: RuleDefinition`` at module
bottom. This package's job is one-line: gather them all into
``STRUCTURAL_RULES``. To add a new metric, drop a new module here
exporting ``RULE`` and list it below.

Cross-cutting rules that emit at graph or whole-repo granularity
(``hotspots``, ``orphans``) live under ``slop.linter.rules`` instead.
"""
from __future__ import annotations

from slop.linter.types import RuleDefinition

from . import (
    clone_density,
    cognitive,
    combinatorial,
    coupling,
    cyclomatic,
    density,
    dependencies,
    escape_hatches,
    god_module,
    hidden_mutators,
    inheritance_children,
    inheritance_depth,
    magic_literals,
    redundancy,
    rigidity,
    sentinels,
    uselessness,
    volume,
)

STRUCTURAL_RULES: list[RuleDefinition] = [
    # complexity family (multi-scope)
    cyclomatic.RULE,
    cognitive.RULE,
    combinatorial.RULE,
    volume.RULE,
    density.RULE,
    # CK class metrics
    coupling.RULE,
    inheritance_depth.RULE,
    inheritance_children.RULE,
    # function-scope standalone
    hidden_mutators.RULE,
    magic_literals.RULE,
    # module-scope standalone
    god_module.RULE,
    escape_hatches.RULE,
    # parameter-scope standalone
    sentinels.RULE,
    # package-scope standalone
    rigidity.RULE,
    uselessness.RULE,
    # cross-cutting (no scope)
    dependencies.RULE,
    redundancy.RULE,
    clone_density.RULE,
]
