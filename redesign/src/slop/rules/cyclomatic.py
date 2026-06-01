"""complexity.cyclomatic — McCabe cyclomatic complexity (verdict).

Defined at ``{Callable, Class}``: a Callable reports its own CCN; a Class reports
the aggregated sum over its methods (the cyclomatic-weighted WMC). The measurement
lives on the component view (``Component.cyclomatic``) — this rule only thresholds
it and emits.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..component.base import Component
from ..component.identity import ComponentKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..rule import Rule


class CyclomaticRule(Rule):
    name = "complexity.cyclomatic"
    altitudes = frozenset({ComponentKind.CALLABLE, ComponentKind.CLASS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.ERROR,
            thresholds={
                ComponentKind.CALLABLE.value: 10,  # McCabe 1976
                ComponentKind.CLASS.value: 40,     # aggregated WMC; slop calibration
            },
        )

    def check(self, component: Component, config: RuleConfig) -> Iterable[Finding]:
        threshold = config.threshold_for(component.id.kind)
        if threshold is None:
            return
        value = component.cyclomatic()
        if value <= threshold:
            return
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.REDUCE_COMPLEXITY,
            prescription=(
                f"Decompose {component.qualname}: extract cohesive branches into "
                f"named helpers or collapse guard clauses (cyclomatic {value} > {int(threshold)})."
            ),
            severity=config.severity,
            value=value,
            threshold=threshold,
            message=f"cyclomatic complexity {value} exceeds threshold {int(threshold)}",
        )
