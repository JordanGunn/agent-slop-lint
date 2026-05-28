"""``uselessness`` — Zone-of-Uselessness D' threshold per package (Martin 1994).

Uselessness: I > 0.7 AND A > 0.7 — unstable (few or no callers) and
abstract (heavy on interfaces). Abstractions exist but nothing uses
them; the indirection is wasted.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.tags import Tag
from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.types import RuleResult
from slop.linter.rules._architecture import _run_zone_rule
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


_RULE = Tag.USELESSNESS.key

def run(
    structure: Structure, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag Zone-of-Uselessness packages whose D' exceeds the uselessness threshold."""
    return _run_zone_rule(
        structure, rule_config, slop_config,
        rule_name=_RULE,
        zone="uselessness",
        zone_label="Uselessness",
        default_threshold=0.7,
    )

RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='Zone of Uselessness — unstable + abstract packages (Martin 1994)',
    default_severity='warning',
    default_enabled=True,
    threshold_label="uselessness & D' > 0.7",
    run=run,
    scopes=('package',),
)
