"""structure.call-islands — disjoint intra-module call topology (REVIEW verdict).

Defined at ``{Module}``. A module whose callables form ≥2 disconnected islands in
its intra-module call graph is structurally anomalous: the file may be two
concerns wearing one name. But the remedy is disjunctive — split along the
islands, OR the module is an intentional facade — and slop does not adjudicate
intent. So this is a ``REVIEW`` verdict: confident anomaly, deferred remedy. REVIEW
verdicts cap at WARNING by construction (they never gate the build).

This is the legacy "lexical.confusion" reframed as what it actually measures —
structural call topology, not lexical overlap.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..component.base import Component
from ..component.identity import ComponentKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..rule import Rule


class CallIslandsRule(Rule):
    name = "structure.call-islands"
    altitudes = frozenset({ComponentKind.MODULE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.WARNING,  # REVIEW is WARNING-pinned; see emission below
            params={"min_islands": 2, "min_functions": 5},
        )

    def check(self, component: Component, config: RuleConfig) -> Iterable[Finding]:
        islands = component.call_islands()
        # call_islands covers every module callable (each in exactly one island),
        # so the member sum is the module's function population.
        function_count = sum(len(i.members) for i in islands)
        min_islands = int(config.param("min_islands", 2))
        min_functions = int(config.param("min_functions", 5))
        if function_count < min_functions or len(islands) < min_islands:
            return
        sizes = ", ".join(str(len(i.members)) for i in sorted(islands, key=lambda i: -len(i.members)))
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.REVIEW,
            # REVIEW caps at WARNING structurally — emit at WARNING regardless of
            # config (a deferred-remedy finding cannot gate the build).
            severity=Severity.WARNING,
            prescription=(
                f"{component.qualname} splits into {len(islands)} disconnected call-islands "
                f"(sizes {sizes}). Split the module along the islands, or confirm it is an "
                f"intentional facade."
            ),
            value=len(islands),
            threshold=min_islands,
            message=f"{len(islands)} disjoint call-islands across {function_count} callables",
        )
