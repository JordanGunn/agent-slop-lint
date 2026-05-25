"""``complexity.cognitive`` — Cognitive Complexity per Campbell 2018.

Function-scope: per-callable Cognitive Complexity (Campbell 2018).
Class-scope:    sum of method cognitive scores. **Slop calibration** —
                Campbell 2018 only defined function-scope; class-scope
                threshold is an empirical slop choice.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.tags import Tag
from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.linter.types import RuleResult
from slop.structure.metrics._complexity_dispatch import _run_complexity_metric
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.structure.view import Structure


def run_cognitive(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: Config,
) -> RuleResult:
    """Cognitive complexity at function scope (Campbell 2018) and class
    scope (sum of method scores — slop calibration)."""
    return _run_complexity_metric(
        rule_name=Tag.COGNITIVE.key,
        structure=structure,
        rule_config=rule_config,
        slop_config=slop_config,
        function_compute=structure.cognitive,
        class_aggregate=structure.weighted_cognitive,
        function_msg=lambda v, t: f"CogC {v} exceeds {t}",
        class_msg=lambda v, t: f"Class CogC sum {v} exceeds {t}",
    )

RULE = RuleDefinition(
    name=Tag.COGNITIVE.key,
    category=Tag.COMPLEXITY.key,
    description='Cognitive Complexity: Campbell 2018 per function; method-sum per class (slop calibration)',
    default_severity='error',
    default_enabled=True,
    threshold_label='CogC > 15 / Σ > 60',
    run=run_cognitive,
    scopes=('function', 'class'),
)
