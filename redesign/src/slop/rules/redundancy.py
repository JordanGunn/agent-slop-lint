"""structure.redundancy — sibling functions sharing project callees (REVIEW verdict).

Defined at ``{Module}``. When two peer top-level functions both call the same set of
project-defined helpers, the module is signalling either a missing shared helper that
should encapsulate the common calls, or a partial copy of one function into the other
(poor factoring). Either way it is worth a look.

Precision (the legacy false-positive this fixes): only *project-defined* shared callees
count — ubiquitous stdlib methods (``.strip``/``.decode``/``.split``) are filtered out by
the metric via the corpus-wide name index, so two functions that merely both call
``.strip()`` are not reported as redundant. ``min_shared`` (default 3) already excludes
single-helper reuse (legitimate DRY).

Disposition: a confident overlap, but the remedy is disjunctive and judgment-bound
(extract a shared helper, merge the two functions, or accept the overlap as
incidental). So this is a ``REVIEW`` verdict, which caps at WARNING — matching the
legacy severity.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class RedundancyRule(Rule):
    name = "structure.redundancy"
    altitudes = frozenset({ScopeKind.MODULE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # REVIEW verdict → WARNING-pinned. Knobs: overlap count + overlap fraction.
        return RuleConfig(name=cls.name, params={"min_shared": 3, "min_score": 0.5})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_shared = int(config.param("min_shared", 3))
        min_score = float(config.param("min_score", 0.5))
        pairs = Structure.over(component).redundant_siblings(
            min_shared=min_shared, min_score=min_score)
        for pair in pairs:
            shared = ", ".join(pair.shared_callees)
            n = len(pair.shared_callees)
            yield Verdict(
                rule=self.name,
                component=component.id,
                action=Action.REVIEW,
                # REVIEW caps at WARNING structurally (deferred remedy, never gates build).
                severity=Severity.WARNING,
                prescription=(
                    f"'{pair.left}' and '{pair.right}' share {n} project callees ({shared}). "
                    "Extract a shared helper encapsulating the common calls, merge the two "
                    "functions if they are near-copies, or confirm the overlap is incidental."
                ),
                value=n,
                threshold=min_shared,
                message=f"'{pair.left}' and '{pair.right}' share {n} callees: {shared}",
                metadata={"left": pair.left, "right": pair.right,
                          "shared_callees": list(pair.shared_callees)},
            )
