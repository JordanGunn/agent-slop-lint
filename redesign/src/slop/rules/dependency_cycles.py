"""structure.dependency-cycles — import cycles violate the Acyclic Dependencies
Principle (verdict).

Defined at ``{Corpus}``. The Acyclic Dependencies Principle (Lakos 1996; Martin
2002, ch. 20) holds that import cycles prevent independent reasoning about, testing
of, or extraction of any module in the loop — every change ripples around the whole
cycle. ``Structure.dependency_cycles`` runs Tarjan's (1972) SCC algorithm over the
resolved module import graph; this rule emits one verdict per cycle.

Disposition: unlike call-islands (where slop cannot tell if there is even a problem),
a cycle is an *unambiguous* defect with a *singular goal* — break it. Only the
mechanism is open (invert one edge via DIP, extract a shared interface, or merge the
modules). That is the shape of a directed corrective (cf. ``REDUCE_COMPLEXITY``: a
named goal with the exact decomposition left to the implementer), not a REVIEW. So
this is an ordinary verdict carrying ``BREAK_DEPENDENCY_CYCLE`` at default ERROR — a
cycle fails the build, as in the legacy linter. Severity is tunable; ``enabled=false``
disables it.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.locus import narrowest_common_ancestor
from ..metrics.structural.view import Structure
from ..rule import Rule


def _modules(component):
    if component.KIND == ScopeKind.MODULE:
        yield component
        return
    for ch in component.children():
        yield from _modules(ch)


class DependencyCyclesRule(Rule):
    name = "structure.dependency-cycles"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # A cycle is a hard ADP violation: default ERROR (fails the build). No
        # threshold knob — the count that matters is "more than zero". Tune via
        # severity, or disable via enabled=false.
        return RuleConfig(name=cls.name, severity=Severity.ERROR)

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        mod_by_qn = {m.qualname: m for m in _modules(component)}
        for cycle in Structure.over(component).dependency_cycles():
            members = list(cycle.members)
            loop = " → ".join(members + members[:1])  # close the loop visually
            # A cycle spans modules; attribute it to their narrowest common scope
            # (the package if co-located) so it converges with other findings there.
            cycle_scopes = [mod_by_qn[m] for m in members if m in mod_by_qn]
            nca = narrowest_common_ancestor(cycle_scopes) if cycle_scopes else None
            yield Verdict(
                rule=self.name,
                component=nca.id if nca is not None else component.id,
                action=Action.BREAK_DEPENDENCY_CYCLE,
                prescription=(
                    f"Break the import cycle {loop}: invert one dependency (depend on an "
                    "abstraction, DIP), extract the shared code into a module both can "
                    "depend on, or merge the modules if they are truly one concern."
                ),
                severity=config.severity,
                value=len(members),
                threshold=0,
                message=f"import cycle across {len(members)} modules: {loop}",
                metadata={"cycle": members},
            )
