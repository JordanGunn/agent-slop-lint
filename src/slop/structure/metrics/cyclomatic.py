"""``complexity.cyclomatic`` — McCabe CCN (function) / WMC (class).

Function-scope: per-callable McCabe Cyclomatic Complexity (McCabe 1976).
Class-scope:    Weighted Methods per Class — sum of method CCNs
                (Chidamber & Kemerer 1994).
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


def run_cyclomatic(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: Config,
) -> RuleResult:
    """Cyclomatic complexity at function scope (McCabe CCN) and class
    scope (WMC = sum of method CCNs, CK 1994)."""
    return _run_complexity_metric(
        rule_name=Tag.CYCLOMATIC.key,
        structure=structure,
        rule_config=rule_config,
        slop_config=slop_config,
        function_compute=structure.cyclomatic,
        class_aggregate=structure.weighted_methods,
        function_msg=lambda v, t: f"CCN {v} exceeds {t}",
        class_msg=lambda v, t: f"WMC {v} exceeds {t}",
    )

RULE = RuleDefinition(
    name=Tag.CYCLOMATIC.key,
    category=Tag.COMPLEXITY.key,
    description='Cyclomatic Complexity: McCabe CCN per function (1976), WMC per class (CK 1994)',
    default_severity='error',
    default_enabled=True,
    threshold_label='CCN > 10 / WMC > 40',
    run=run_cyclomatic,
    scopes=('function', 'class'),
)
