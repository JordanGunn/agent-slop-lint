"""Rule registry — every rule slop ships, flat.

Each rule module owns its own ``RULE: RuleDefinition`` at module bottom.
This package's job is one line: gather them all into ``RULE_REGISTRY``.

There is no substrate sub-grouping at the directory level — a rule's
package location does not imply which view it consumes. The rule's
imports (``from slop.structure.view import Structure`` etc.) are the
authoritative signal. Substrate grouping was vestigial from the
retired ``structural.*`` / ``lexical.*`` name prefixes; the rule names
are bare now (``complexity.cyclomatic``, ``lexical.stutter``,
``hotspots``) and the layout follows the names.
"""
from __future__ import annotations

from slop.linter.types import RuleDefinition

from . import (
    clone_density,
    cognitive,
    combinatorial,
    confusion,
    coupling,
    cyclomatic,
    density,
    dependencies,
    escape_hatches,
    god_module,
    hammers,
    hidden_mutators,
    hotspots,
    imposters,
    inheritance_children,
    inheritance_depth,
    magic_literals,
    orphans,
    redundancy,
    rigidity,
    runts,
    sentinels,
    slackers,
    sprawl,
    stutter,
    uselessness,
    verbosity,
    volume,
)

RULE_REGISTRY: list[RuleDefinition] = [
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
    # graph / whole-tree (no scope)
    dependencies.RULE,
    redundancy.RULE,
    clone_density.RULE,
    # lexical (naming discipline over Lexicon view)
    stutter.RULE,
    verbosity.RULE,
    hammers.RULE,
    sprawl.RULE,
    imposters.RULE,
    slackers.RULE,
    confusion.RULE,
    runts.RULE,
    # cross-cutting (need git churn or whole-repo ripgrep)
    hotspots.RULE,
    orphans.RULE,
]
