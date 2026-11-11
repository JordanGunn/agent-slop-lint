"""duplicate-code: callables with structurally identical bodies (Type-2 clones).

Defined at the corpus altitude. A Type-2 clone is a set of callables whose bodies have the
same AST leaf-type fingerprint, differing only in identifiers and literals: the
copy-paste-then-rename signature. The rule reports one violation per cluster, at its first
member (by path, then line), and names every member as ``path:line qualname``.

``min_leaf_nodes`` (default 10) skips trivial bodies.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..config import RuleConfig
from ..identity import relative_path
from ..metrics.structural.view import Structure
from ..rule import Rule
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..violation import Violation


class DuplicationRule(Rule):
    name = "duplicate-code"
    description = "callables have structurally identical bodies (Type-2 clones)"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, options={"min_leaf_nodes": 10})

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
                message=f"{len(cluster.members)} Type-2 clones ({cluster.leaf_count} leaf nodes): {members}",
                value=len(cluster.members),
                threshold=2,
                subject=first.qualname,
            )
