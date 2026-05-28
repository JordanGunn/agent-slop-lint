"""``rigidity`` — Zone-of-Pain D' threshold per package (Martin 1994).

Pain: I < 0.3 AND A < 0.3 — stable (many callers) and concrete (no
abstractions to substitute through). The package is locked in by its
callers and lacks extension points.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.tags import Tag
from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.types import RuleResult
from slop.linter.rules.architecture import _run_zone_rule
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


_RULE = Tag.RIGIDITY.key

def run(
    structure: Structure, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag Zone-of-Pain packages whose D' exceeds the rigidity threshold."""
    return _run_zone_rule(
        structure, rule_config, slop_config,
        rule_name=_RULE,
        zone="pain",
        zone_label="Pain",
        default_threshold=0.7,
    )

RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='Zone of Pain — stable + concrete packages (Martin 1994)',
    default_severity='warning',
    default_enabled=True,
    threshold_label="pain & D' > 0.7",
    run=run,
    scopes=('package',),
)
