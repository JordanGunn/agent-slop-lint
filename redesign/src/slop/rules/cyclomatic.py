"""complexity.cyclomatic — McCabe cyclomatic complexity (verdict).

Defined at ``{Callable}`` only. McCabe complexity measures control-flow paths
*within a unit*; the class-altitude aggregate (Σ of method CCNs, the
cyclomatic-weighted WMC) does not measure any unit's control flow — it is
dominated by method count, so it conflates breadth with tangle. Empirically every
class that tripped a class-altitude gate was either pure breadth (many trivial
methods, no method over CCN 10) or had a single tangled method already flagged
here at the Callable altitude — so the class gate only ever produced breadth
false-positives or callable-gate duplicates. Class *size* belongs to a future
NOM/god-class rule, not to cyclomatic. The aggregate measurement still exists on
``Component.cyclomatic`` for any consumer that wants it; it is simply not gated.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Component
from ..scope.identity import ComponentKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class CyclomaticRule(Rule):
    name = "complexity.cyclomatic"
    altitudes = frozenset({ComponentKind.CALLABLE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.ERROR,
            thresholds={ComponentKind.CALLABLE.value: 10},  # McCabe 1976
        )

    def check(self, component: Component, config: RuleConfig) -> Iterable[Finding]:
        threshold = config.threshold_for(component.id.kind)
        if threshold is None:
            return
        value = Structure.over(component).cyclomatic()
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
