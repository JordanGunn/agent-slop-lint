"""structure.rigidity — Martin's Zone of Pain, per package (REVIEW verdict).

Defined at ``{Package}``. A package is *rigid* when it is both stable (many
inbound dependents, low instability I) and concrete (few abstractions, low
abstractness A): callers are locked to it yet there is nothing to substitute
through. Martin (1994) places such packages in the "Zone of Pain", far from the
main sequence ``A + I = 1`` — the normalised distance ``D' = |A + I - 1|`` is large.

Zone membership (``I < 0.3 and A < 0.3``) is the metric layer's call
(``in_zone_of_pain``); the rule adds a ``D'`` *depth* gate (default 0.7) so only
packages deep in the corner fire, not every package grazing the boundary. This is
the legacy ``zone == pain AND D' > 0.7`` predicate, preserved.

Disposition: the anomaly is confident but the remedy is disjunctive and
judgment-bound — introduce abstractions to depend on, *or* reduce inbound coupling,
depending on why the package is load-bearing. So this is a ``REVIEW`` verdict, which
caps at WARNING by construction (it never gates the build).
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class RigidityRule(Rule):
    name = "structure.rigidity"
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
        if not view.in_zone_of_pain():
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
                f"{component.qualname} sits in Martin's Zone of Pain "
                f"(D'={m.distance:.2f} > {threshold}; I={m.instability:.2f}, "
                f"A={m.abstractness:.2f}): stable (many dependents) yet concrete (few "
                "abstractions). Introduce abstractions for dependents to bind to, or "
                "reduce inbound coupling — confirm which fits before acting."
            ),
            value=m.distance,
            threshold=threshold,
            message=(
                f"Zone of Pain: D'={m.distance:.2f} "
                f"(I={m.instability:.2f}, A={m.abstractness:.2f})"
            ),
        )
