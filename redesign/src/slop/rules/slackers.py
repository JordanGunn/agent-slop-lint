"""lexical.slackers — sibling functions refusing to align by naming (verdict).

Fires on a *real* first-parameter cluster (one imposters would profile as
``missing_class`` or ``heterogeneous``) whose member names do not fit a common token
template. The cluster is a structural family; the names refuse to admit it. slop catches
what humans rarely fix in agent-written code — each name reads fine alone, only the
family fails to communicate.

Template coverage = the fraction of members captured by an affix pattern with ≥2
variants (``build_affix_patterns``). Coverage ≤ ``max_coverage`` (default 0.30) means
the names are not aligned. Disposition: ``missing_class`` → directed
``RENAME_BY_TEMPLATE`` (the cluster is real; adopt a scheme); ``heterogeneous`` →
``REVIEW`` (some members may not belong).

Battery: paired with ``lexical.imposters`` — both consume the same clusters, so they
co-fire on a genuine missing-class cluster with inconsistent names (extract a class AND
align the names). Converging concerns on one target is the priority signal, not
double-counting.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.lexical import Lexical
from ..metrics.lexical.affix import UNIVERSAL_NOISE, Lexeme, build_affix_patterns
from ..rule import Rule

_REAL_PROFILES = frozenset({"missing_class", "heterogeneous"})


class SlackersRule(Rule):
    name = "lexical.slackers"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, severity=Severity.WARNING,
                          params={"min_cluster": 3, "max_coverage": 0.30})

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
            line = min((m[2] for m in cluster.members), default=0)
            locus = cluster.locus or component.id
            if cluster.profile_label == "missing_class":
                yield Verdict(
                    rule=self.name, component=locus, action=Action.RENAME_BY_TEMPLATE,
                    prescription=(
                        f"Adopt a naming template across the {len(cluster.members)} functions "
                        f"sharing '{cluster.parameter_name}' ({names}): the cluster is real "
                        f"({coverage:.0%} template coverage). Use verb_{cluster.parameter_name} "
                        f"or {cluster.parameter_name}_attribute consistently."
                    ),
                    severity=config.severity, value=round(coverage, 3), threshold=max_coverage,
                    line=line,
                    message=f"'{cluster.parameter_name}' cluster names don't align ({coverage:.0%} template coverage)",
                    metadata={"parameter": cluster.parameter_name, "profile": cluster.profile_label,
                              "coverage": round(coverage, 3), "members": [m[0] for m in cluster.members]},
                )
            else:  # heterogeneous
                yield Verdict(
                    rule=self.name, component=locus, action=Action.REVIEW,
                    severity=Severity.WARNING,  # REVIEW caps at WARNING
                    prescription=(
                        f"Review whether the {len(cluster.members)} members of the "
                        f"'{cluster.parameter_name}' cluster ({names}) all belong — it is "
                        "structurally mixed and the names do not align; low-coverage members "
                        "may be helpers that should be relocated."
                    ),
                    value=round(coverage, 3), threshold=max_coverage, line=line,
                    message=f"'{cluster.parameter_name}' heterogeneous cluster, names don't align ({coverage:.0%})",
                    metadata={"parameter": cluster.parameter_name, "profile": cluster.profile_label,
                              "coverage": round(coverage, 3), "members": [m[0] for m in cluster.members]},
                )
