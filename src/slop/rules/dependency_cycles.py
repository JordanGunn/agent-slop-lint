"""import-cycle: modules that import each other in a loop.

Defined at the corpus altitude. The Acyclic Dependencies Principle (Lakos 1996; Martin
2002, ch. 20) holds that a cycle stops any module in it being reasoned about, tested or
extracted alone. ``Structure.dependency_cycles`` finds strongly connected components of
the resolved module import graph (Tarjan 1972); this rule reports one violation per
cycle, at its first module (by path), naming every member by its path.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..config import RuleConfig
from ..metrics.structural.view import Structure
from ..rule import Rule
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from ..violation import Violation


class DependencyCyclesRule(Rule):
    name = "import-cycle"
    description = "modules import each other in a cycle (Acyclic Dependencies Principle)"
    altitudes = frozenset({ScopeKind.CORPUS})


    def check(self, scope: Scope, config: RuleConfig) -> Iterable[Violation]:
        mod_by_id = {m.id: m for m in scope._iter_modules()}
        for cycle in Structure.over(scope).dependency_cycles():
            members = list(cycle.members)
            loop = " → ".join(members + members[:1])
            anchor = mod_by_id.get(cycle.scopes[0]) if cycle.scopes else None
            message = f"import cycle across {len(members)} modules: {loop}"
            if anchor is not None:
                yield Violation.at(anchor, self.name, message, value=len(members), threshold=0,
                                   related=tuple(cycle.scopes[1:]))
            else:
                yield Violation(rule=self.name, path=None, line=1, column=1, message=message,
                                value=len(members), threshold=0, related=tuple(cycle.scopes))
