"""structure.duplication — Type-2 clone clusters across the corpus (verdict).

Defined at ``{Corpus}``. A Type-2 clone is a set of callables with structurally
identical bodies (same AST leaf-type fingerprint) differing only in identifiers
and literals — the copy-paste-then-rename signature. Each cluster is independently
actionable regardless of overall codebase size, so the rule emits one
``EXTRACT_HELPER`` verdict per cluster (the legacy emitted per-cluster findings
unconditionally; its separate corpus-density summary line does not map to a
per-component verdict and is dropped — a candidate future observation).

``min_leaf_nodes`` (default 10) skips trivial one-liner bodies — a noise floor,
not a claim. Cluster size is structurally floored at 2 (a clone needs two members);
it is not a config knob (a min_cluster_size=1 would be meaningless).

Limitation: the CloneCluster record carries member qualnames, not locations, so the
verdict names the members rather than pinpointing one — addressable when the record
grows a ScopeId/line.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class DuplicationRule(Rule):
    name = "structure.duplication"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.WARNING,
            params={"min_leaf_nodes": 10},
        )

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_leaf_nodes = int(config.param("min_leaf_nodes", 10))
        clusters = Structure.over(component).clone_clusters(min_leaf_nodes=min_leaf_nodes)
        for cluster in clusters:
            members = ", ".join(cluster.members)
            yield Verdict(
                rule=self.name,
                component=cluster.locus or component.id,
                action=Action.EXTRACT_HELPER,
                prescription=(
                    f"Extract a shared helper: {len(cluster.members)} functions are Type-2 "
                    f"clones (structurally identical bodies, {cluster.leaf_count} leaf nodes) "
                    f"— {members}."
                ),
                severity=config.severity,
                value=len(cluster.members),
                threshold=2,
                message=f"{len(cluster.members)} Type-2 clones: {members}",
            )
