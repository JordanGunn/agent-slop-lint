"""structure.god-module — too many top-level definitions in one module (verdict).

Defined at ``{Module}``. A module that declares many unrelated top-level symbols
resists focused ownership, makes test isolation expensive, and forces every reader
to skim the whole file to grasp its scope. The metric is a *count* (breadth), not a
complexity (depth): methods inside classes do not count (that is a god-class /WMC
signal), and lambdas do not count (inline values, not definitions). Structure's
``definition_count`` is exactly this — the module's direct CALLABLE/CLASS children.

Threshold is the legacy default (> 20 top-level definitions).
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class GodModuleRule(Rule):
    name = "structure.god-module"
    altitudes = frozenset({ScopeKind.MODULE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.WARNING,
            thresholds={ScopeKind.MODULE.value: 20},
        )

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        threshold = config.threshold_for(component.id.kind)
        if threshold is None:
            return
        value = Structure.over(component).definition_count()
        if value <= threshold:
            return
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.SPLIT_MODULE,
            prescription=(
                f"Split {component.qualname}: {value} top-level definitions exceeds "
                f"{int(threshold)}. Group related definitions into focused modules."
            ),
            severity=config.severity,
            value=value,
            threshold=threshold,
            message=f"{value} top-level definitions exceeds threshold {int(threshold)}",
        )
