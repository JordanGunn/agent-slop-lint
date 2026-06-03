"""structure.uselessness — Martin's Zone of Uselessness, per package (REVIEW verdict).

Defined at ``{Package}``. A package is *useless* when it is both unstable (few or
no inbound dependents, high instability I) and abstract (heavy on interfaces, high
abstractness A): the abstractions exist but almost nothing depends on them, so the
indirection is unpaid-for. Martin (1994) places such packages in the "Zone of
Uselessness", far from the main sequence ``A + I = 1`` on the opposite corner from
the Zone of Pain — ``D' = |A + I - 1|`` is again large.

Zone membership (``I > 0.7 and A > 0.7``) is the metric layer's call
(``in_zone_of_uselessness``); the rule adds a ``D'`` *depth* gate (default 0.7) so
only packages deep in the corner fire. This is the legacy ``zone == uselessness AND
D' > 0.7`` predicate, preserved.

Disposition: the remedy is disjunctive and judgment-bound — find or attract the
callers the abstraction was built for, *or* delete the unused indirection. So this
is a ``REVIEW`` verdict, which caps at WARNING by construction.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class UselessnessRule(Rule):
    name = "structure.uselessness"
    altitudes = frozenset({ScopeKind.PACKAGE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # REVIEW verdict → WARNING-pinned; no severity knob. The only knob is the
        # D' depth past zone membership, carried as the package-altitude threshold.
        return RuleConfig(name=cls.name, thresholds={ScopeKind.PACKAGE.value: 0.7})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        threshold = config.threshold_for(component.id.kind)
        if threshold is None:
            return
        view = Structure.over(component)
        if not view.in_zone_of_uselessness():
            return
        m = view.martin_metrics()
        if m.distance <= threshold:
            return
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.REVIEW,
            # REVIEW caps at WARNING structurally — a deferred-remedy finding
            # cannot gate the build, so emit at WARNING regardless of config.
            severity=Severity.WARNING,
            prescription=(
                f"{component.qualname} sits in Martin's Zone of Uselessness "
                f"(D'={m.distance:.2f} > {threshold}; I={m.instability:.2f}, "
                f"A={m.abstractness:.2f}): abstract (heavy on interfaces) yet unstable "
                "(few or no dependents). Find or attract the callers the abstraction "
                "was built for, or delete the unused indirection — confirm which fits."
            ),
            value=m.distance,
            threshold=threshold,
            message=(
                f"Zone of Uselessness: D'={m.distance:.2f} "
                f"(I={m.instability:.2f}, A={m.abstractness:.2f})"
            ),
        )
