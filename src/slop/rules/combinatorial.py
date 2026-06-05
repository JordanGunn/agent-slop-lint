"""complexity.combinatorial — NPath complexity (Nejmeh 1988) (verdict).

Defined at ``{Callable}`` only. NPath counts the *acyclic execution paths*
through a unit — it multiplies across sequential branch points, so it captures
combinatorial blow-up that the additive cyclomatic count flattens (two sequential
3-way branches: cyclomatic 4, NPath 9). The legacy rule also gated a class-scope
sum of method NPaths, but that was self-described "slop calibration, no published
threshold" — the same breadth-vs-tangle conflation the cyclomatic and cognitive
rules already reject at the class altitude. Nejmeh 1988 defined NPath at function
scope; the aggregate still exists on ``Structure.combinatorial`` for any consumer,
it is simply not gated. Class size belongs to a future NOM/god-class rule.

Threshold is the legacy standard-profile default (NPath > 400). Nejmeh's own
recommendation was 200; slop's shipped default doubled it for agent-generated
code, where the published academic limit floods.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class CombinatorialRule(Rule):
    name = "complexity.combinatorial"
    altitudes = frozenset({ScopeKind.CALLABLE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.ERROR,
            thresholds={ScopeKind.CALLABLE.value: 400},  # Nejmeh 1988 (200), slop std profile
        )

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        threshold = config.threshold_for(component.id.kind)
        if threshold is None:
            return
        value = Structure.over(component).combinatorial()
        if value <= threshold:
            return
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.REDUCE_COMPLEXITY,
            prescription=(
                f"Reduce branching in {component.qualname}: collapse sequential "
                f"conditionals or extract a branch-heavy section into a named helper "
                f"(NPath {value} > {int(threshold)})."
            ),
            severity=config.severity,
            value=value,
            threshold=threshold,
            message=f"NPath complexity {value} exceeds threshold {int(threshold)}",
        )
