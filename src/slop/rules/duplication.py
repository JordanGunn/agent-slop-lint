"""duplicate-code: callables whose bodies are the same code up to renaming (Baker 1995).

Defined at the corpus altitude. A clone is a set of callables whose bodies match token for
token, except for the names each body binds (parameters, assigned locals, loop variables),
which may be consistently renamed, and literal values: the copy-paste-then-rename signature.
A different callee, member or keyword argument is different code. The rule reports one violation per cluster, at its first
member (by path, then line), and names every member as ``path:line qualname``.

``min_leaf_nodes`` (default 10) skips trivial bodies.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..config import RuleConfig
from ..identity import relative_path
from ..metrics.structural.view import Structure
from ..rule import Rule
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from ..violation import Violation


class DuplicationRule(Rule):
    name = "duplicate-code"
    description = "callables have the same code up to renaming their own names (parameterized clones)"
    altitudes = frozenset({ScopeKind.CORPUS})

    default_options = {"min_leaf_nodes": 10}

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Violation]:
        clusters = Structure.over(component).clone_clusters(
            min_leaf_nodes=config.option("min_leaf_nodes"))
        for cluster in clusters:
            members = ", ".join(
                f"{relative_path(m.scope, component.root) or '?'}:{m.line} {m.qualname}"
                for m in cluster.members)
            first = cluster.members[0]
            span = first.scope.spans[0] if first.scope.spans else None
            yield Violation(
                rule=self.name,
                path=span.path if span else None,
                line=first.line or 1,
                column=1,
                message=f"{len(cluster.members)} clones ({cluster.leaf_count} leaf nodes): {members}",
                value=len(cluster.members),
                threshold=2,
                subject=first.qualname,
                scope=first.scope,
                related=tuple(m.scope for m in cluster.members[1:]),
            )
