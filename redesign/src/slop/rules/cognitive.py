"""complexity.cognitive — Cognitive Complexity (Campbell 2018) (verdict).

Defined at ``{Callable}`` only. Cognitive Complexity scores how hard a unit is to
*follow* — it rewards flat control flow and penalises nesting — which is a
distinct signal from cyclomatic's path count (the two co-fire but a deeply-nested
3-path function and a flat 8-path one are not the same defect). The legacy rule
also gated a class-scope aggregate (Σ of method scores), but that was explicitly
"slop calibration", not Campbell — and it is the same breadth-vs-tangle conflation
the cyclomatic rule already rejects at the class altitude: a class sum is
dominated by method count, so it flags pure breadth or duplicates a method already
flagged here. Campbell 2018 defined the metric at function scope only; the
aggregate still exists on ``Structure.cognitive`` for any consumer, it is simply
not gated. Class size belongs to a future NOM/god-class rule.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class CognitiveRule(Rule):
    name = "complexity.cognitive"
    altitudes = frozenset({ScopeKind.CALLABLE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.ERROR,
            thresholds={ScopeKind.CALLABLE.value: 15},  # Campbell 2018
        )

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        threshold = config.threshold_for(component.id.kind)
        if threshold is None:
            return
        value = Structure.over(component).cognitive()
        if value <= threshold:
            return
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.REDUCE_COMPLEXITY,
            prescription=(
                f"Flatten {component.qualname}: lift nested conditionals into guard "
                f"clauses or extract the deepest branch into a named helper "
                f"(cognitive {value} > {int(threshold)})."
            ),
            severity=config.severity,
            value=value,
            threshold=threshold,
            message=f"cognitive complexity {value} exceeds threshold {int(threshold)}",
        )
