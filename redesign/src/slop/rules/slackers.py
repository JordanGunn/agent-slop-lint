"""lexical.slackers — sibling functions refusing to align by naming (observation).

Fires on a *real* first-parameter cluster (one imposters would profile as
``missing_class`` or ``heterogeneous``) whose member names do not fit a common token
template. The cluster is a structural family; the names refuse to admit it. slop catches
what humans rarely fix in agent-written code — each name reads fine alone, only the
family fails to communicate.

Template coverage = the fraction of members captured by an affix pattern with ≥2
variants (``build_affix_patterns``). Coverage ≤ ``max_coverage`` (default 0.30) means
the names are not aligned.

Disposition (per the disposition policy): both the cluster and the misalignment are
*inferred* — the cluster from a probabilistic profile, the "should align" from a naming
template. An inferred pattern must not fire a *directive* verdict; the old
``RENAME_BY_TEMPLATE`` verdict over-claimed. So this is an ``OBSERVATION``: the
misalignment is real evidence, but slop cannot honestly prescribe the rename (which
template? do all members even belong?). The agent investigates.

Battery (the future upgrade): paired with ``lexical.imposters`` over the same clusters —
imposters asks "is this a class?", slackers asks "do the names align?". When they
co-fire on one cluster and a structural signal corroborates, the battery can promote to
a ``REVIEW`` verdict (extract a class AND align the names). Converging concerns on one
target is the priority signal, not double-counting.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Evidence, Finding, Observation
from ..metrics.lexical import Lexical
from ..metrics.lexical.affix import UNIVERSAL_NOISE, Lexeme, build_affix_patterns
from ..rule import Rule

_REAL_PROFILES = frozenset({"missing_class", "heterogeneous"})


class SlackersRule(Rule):
    name = "lexical.slackers"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, params={"min_cluster": 3, "max_coverage": 0.30})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_cluster = int(config.param("min_cluster", 3))
        max_coverage = float(config.param("max_coverage", 0.30))
        clusters = Lexical.over(component).first_param_clusters(
            min_cluster=min_cluster, root=getattr(component, "root", None))

        for cluster in clusters:
            if cluster.profile_label not in _REAL_PROFILES:
                continue
            items = [Lexeme.of(name) for name, _f, _l in cluster.members]
            patterns = build_affix_patterns(items, exclude=UNIVERSAL_NOISE)
            meaningful = [p for p in patterns
                          if sum(len(v) for v in p.variants.values()) >= 2]
            covered: set[str] = set()
            for p in meaningful:
                for variant_members in p.variants.values():
                    for n, _f, _l in variant_members:
                        covered.add(n)
            coverage = len(covered) / len(items) if items else 0.0
            if coverage > max_coverage:
                continue

            names = ", ".join(sorted(n for n, _f, _l in cluster.members))
            locus = cluster.locus or component.id
            if cluster.profile_label == "missing_class":
                message = (
                    f"{len(cluster.members)} functions sharing '{cluster.parameter_name}' "
                    f"({names}) are a real cluster ({coverage:.0%} template coverage) whose "
                    f"names don't align — the family is real, the names hide it. Consider a "
                    f"consistent template (verb_{cluster.parameter_name} or "
                    f"{cluster.parameter_name}_attribute)."
                )
            else:  # heterogeneous
                message = (
                    f"the {len(cluster.members)} members of the '{cluster.parameter_name}' "
                    f"cluster ({names}) are structurally mixed and the names don't align "
                    f"({coverage:.0%} coverage) — some low-coverage members may be helpers "
                    "that belong elsewhere. Confirm which members belong."
                )
            yield Observation(
                rule=self.name,
                component=locus,
                evidence=Evidence(kind="naming-misalignment", data={
                    "parameter": cluster.parameter_name, "profile": cluster.profile_label,
                    "coverage": round(coverage, 3),
                    "members": [m[0] for m in cluster.members]}),
                message=message,
                metadata={"parameter": cluster.parameter_name, "profile": cluster.profile_label,
                          "coverage": round(coverage, 3),
                          "members": [m[0] for m in cluster.members]},
            )
