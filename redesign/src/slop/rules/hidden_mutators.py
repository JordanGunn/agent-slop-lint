"""structure.hidden-mutators — in-place mutation of parameters (REVIEW verdict).

Defined at ``{Callable}``. A function that mutates a passed-in collection or
reference in place (``param.append(...)``, ``*p = x``, ``p->field = y``, …) has an
out-parameter: the caller's data changes as a side effect. That makes call-site
reasoning harder and often signals the function should return a new value instead.

Disposition: slop is confident about the *fact* (the mutation is in the AST), but
the remedy depends on intent it cannot read — an accumulator, visitor, or
performance-critical in-place update is legitimate, while an accidental aliasing bug
is not. So this is a ``REVIEW`` verdict (confident anomaly, intent-dependent remedy),
which caps at WARNING — matching the legacy severity.

``min_mutations`` (default 1) gates how many in-place mutations a callable must show
before it is flagged.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class HiddenMutatorsRule(Rule):
    name = "structure.hidden-mutators"
    altitudes = frozenset({ScopeKind.CALLABLE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # REVIEW verdict → WARNING-pinned; the only knob is the mutation-count floor.
        return RuleConfig(name=cls.name, params={"min_mutations": 1})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_mutations = int(config.param("min_mutations", 1))
        mutations = Structure.over(component).mutated_parameters()
        if len(mutations) < min_mutations:
            return
        params = sorted({m.parameter for m in mutations})
        kinds = sorted({m.kind for m in mutations})
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.REVIEW,
            # REVIEW caps at WARNING structurally (deferred-remedy, never gates build).
            severity=Severity.WARNING,
            prescription=(
                f"{component.qualname} mutates parameter(s) {', '.join(params)} in place "
                f"({', '.join(kinds)}). Return a new value instead, or confirm the in-place "
                "mutation is the intended contract (accumulator/visitor) and document it."
            ),
            value=len(mutations),
            threshold=min_mutations,
            message=f"mutates parameter(s) {', '.join(params)} in place",
            metadata={"parameters": params, "kinds": kinds},
        )
