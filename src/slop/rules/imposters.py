"""lexical.imposters — parameters camouflaged as ordinary dependencies (observation).

A cluster of functions sharing a first parameter that they all treat as a *receiver*
(``param.attr`` access, shared body shape) is a class in hiding — the parameter is the
implicit ``self``. ``Lexical.first_param_clusters`` surfaces these clusters and profiles
each.

Disposition (per the disposition policy — see DESIGN.md "Finding Ontology"): a
first-parameter cluster is an *inferred* pattern, not an exact one. The profile
classifier is a probabilistic judgement (cf. the complexity-decomposition tension,
where extracting helpers manufactures first-param clusters that are *not* missing
classes). An inferred pattern must not fire a *directive* verdict — the old
``EXTRACT_CLASS`` verdict claimed a certainty the signal does not carry. So this rule
now emits an ``OBSERVATION``: the cluster is real evidence worth surfacing, but slop
cannot honestly prescribe the extraction. The agent reads the evidence and decides.

Surfaced profiles:

- ``missing_class`` — high receiver-call density + body-shape cohesion: the textbook
  class-extraction candidate (the strongest evidence; the message says so).
- ``dispatch_family`` / ``heterogeneous`` — a real shared input but the refactor is not
  determined (tabular dispatch? keep as free functions? coincidence?).

Other profiles (``strategy_family``, ``infrastructure``, ``false_positive``,
``unknown``) are not surfaced — not even evidence slop wants to nudge on.

Battery (the future upgrade to a verdict): paired with ``lexical.slackers`` over the
same clusters, and with structural clones/redundancy. When an independent structural
signal corroborates a cluster, the battery can promote to a ``REVIEW`` verdict — a
single inferred signal cannot.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Evidence, Finding, Observation, Severity, Verdict
from ..metrics.lexical import Lexical
from ..rule import Rule
from ._battery import corroboration_groups, is_corroborated

# Profiles worth surfacing as evidence. missing_class is the strongest; the other two
# are real shared inputs with an undetermined remedy.
_SURFACED = frozenset({"missing_class", "dispatch_family", "heterogeneous"})


class ImpostersRule(Rule):
    name = "lexical.imposters"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, params={"min_cluster": 3})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_cluster = int(config.param("min_cluster", 3))
        clusters = Lexical.over(component).first_param_clusters(
            min_cluster=min_cluster, root=getattr(component, "root", None))
        surfaced = [c for c in clusters if c.profile_label in _SURFACED]
        if not surfaced:
            return
        groups = corroboration_groups(component)  # built once per run

        for c in surfaced:
            member_names = {m[0] for m in c.members}
            members = ", ".join(sorted(member_names))
            locus = c.locus or component.id
            data = {"parameter": c.parameter_name, "profile": c.profile_label,
                    "members": [m[0] for m in c.members], "size": len(c.members),
                    "scope": c.scope}

            if is_corroborated(member_names, groups):
                # An independent structural signal (clones / redundant siblings) binds
                # the cluster — corroborated, so promote to a REVIEW verdict.
                yield Verdict(
                    rule=self.name, component=locus, action=Action.REVIEW,
                    severity=Severity.WARNING,  # REVIEW caps at WARNING
                    prescription=(
                        f"{len(c.members)} functions ({members}) share receiver "
                        f"'{c.parameter_name}' AND an independent structural signal binds them "
                        "(Type-2 clones or shared project callees) — corroborated evidence of a "
                        "class in hiding. Extract a class with the receiver as self, or confirm "
                        "the structural overlap is incidental."
                    ),
                    value=len(c.members), threshold=min_cluster,
                    message=f"corroborated receiver cluster '{c.parameter_name}' ({c.profile_label})",
                    metadata={**data, "corroborated": True},
                )
                continue

            if c.profile_label == "missing_class":
                message = (
                    f"{len(c.members)} functions ({members}) share first parameter "
                    f"'{c.parameter_name}' and use it as a receiver (attribute access + shared "
                    f"body shape) — a class in hiding. Likely extract a class with "
                    f"'{c.parameter_name}' as self, once the shared shape is confirmed real."
                )
            else:
                message = (
                    f"{len(c.members)} functions ({members}) share first parameter "
                    f"'{c.parameter_name}' ({c.profile_label.replace('_', ' ')}) — a real shared "
                    "input whose refactor is undetermined (class? tabular dispatch? coincidence?). "
                    "Confirm intent before refactoring."
                )
            yield Observation(
                rule=self.name,
                component=locus,
                evidence=Evidence(kind="receiver-cluster", data=data),
                message=message,
                metadata=data,
            )
