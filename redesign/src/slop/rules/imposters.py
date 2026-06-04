"""lexical.imposters — parameters camouflaged as ordinary dependencies (verdict).

A cluster of functions sharing a first parameter that they all treat as a *receiver*
(``param.attr`` access, shared body shape) is a class in hiding — the parameter is the
implicit ``self``. ``Lexical.first_param_clusters`` surfaces these clusters and profiles
each; this rule turns the profile into a verdict:

- ``missing_class`` — high receiver-call density + body-shape cohesion: the textbook
  class extraction. Directed ``EXTRACT_CLASS`` verdict.
- ``dispatch_family`` / ``heterogeneous`` — a real shared input but the refactor is not
  determined (tabular dispatch? keep as free functions? genuinely unrelated?). ``REVIEW``.
- ``strategy_family`` (body-clones, no receiver use), ``infrastructure``,
  ``false_positive``, ``unknown`` — skipped: not a defect slop can claim (the strategy
  family is an accept-as-idiomatic note, cut per structural-not-style).

Battery: paired with ``lexical.slackers`` over the same clusters — imposters asks "is
this a class?", slackers asks "do the names align?". Complementary, not double-counting.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.lexical import Lexical
from ..rule import Rule

_REVIEW_PROFILES = frozenset({"dispatch_family", "heterogeneous"})


class ImpostersRule(Rule):
    name = "lexical.imposters"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, severity=Severity.WARNING, params={"min_cluster": 3})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_cluster = int(config.param("min_cluster", 3))
        clusters = Lexical.over(component).first_param_clusters(
            min_cluster=min_cluster, root=getattr(component, "root", None))
        for c in clusters:
            members = ", ".join(sorted(m[0] for m in c.members))
            line = min((m[2] for m in c.members), default=0)
            locus = c.locus or component.id
            if c.profile_label == "missing_class":
                yield Verdict(
                    rule=self.name, component=locus, action=Action.EXTRACT_CLASS,
                    prescription=(
                        f"Extract a class around '{c.parameter_name}': {len(c.members)} functions "
                        f"({members}) share it and use it as a receiver (attribute access + shared "
                        "body shape). The parameter is an implicit self — make it explicit."
                    ),
                    severity=config.severity, value=len(c.members), threshold=min_cluster,
                    line=line,
                    message=f"missing class around receiver '{c.parameter_name}' ({len(c.members)} methods)",
                    metadata={"parameter": c.parameter_name, "profile": c.profile_label,
                              "members": [m[0] for m in c.members], "scope": c.scope},
                )
            elif c.profile_label in _REVIEW_PROFILES:
                yield Verdict(
                    rule=self.name, component=locus, action=Action.REVIEW,
                    severity=Severity.WARNING,  # REVIEW caps at WARNING
                    prescription=(
                        f"{len(c.members)} functions ({members}) share first parameter "
                        f"'{c.parameter_name}' ({c.profile_label.replace('_', ' ')}). Confirm "
                        "whether this is a class, a tabular dispatch, or unrelated coincidence "
                        "before refactoring."
                    ),
                    value=len(c.members), threshold=min_cluster, line=line,
                    message=f"shared-receiver cluster '{c.parameter_name}' ({c.profile_label})",
                    metadata={"parameter": c.parameter_name, "profile": c.profile_label,
                              "members": [m[0] for m in c.members], "scope": c.scope},
                )
