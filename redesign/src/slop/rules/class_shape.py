"""class-shape — the Chidamber-Kemerer (1994) suite as a class observation.

Defined at ``{Class}``. Emits a claim-free OBSERVATION (never a verdict) carrying a
class's CK profile — CBO (coupling between objects), DIT (depth of inheritance tree),
NOC (number of children), NOM (number of methods) — for any class whose profile is
*notable*. The CK metrics are descriptive class-shape measures, not defects:

- NOC is genuinely ambiguous — a class with many direct subclasses is frequently a
  healthy abstraction (an ABC with many implementers), not a god-base.
- DIT/NOC are inputs to the future taxonomic-degradation battery (NA-default base
  method + strict-subset override + directional churn); a standalone threshold would
  be both false precision and premature, subsumed once the battery lands.

So this surfaces the evidence and lets the consuming agent judge. The legacy CK
thresholds (CBO>8, DIT>4, NOC>10) survive as **attention floors** — they gate output
volume (which classes are worth narrating), not pass/fail. First Class-altitude rule
and first rule to drive the analysis-context ``class_index``.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Evidence, Finding, Observation, Severity
from ..metrics.structural.view import Structure
from ..rule import Rule


class ClassShapeRule(Rule):
    name = "class-shape"
    altitudes = frozenset({ScopeKind.CLASS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # Attention floors (legacy CK thresholds), repurposed to gate output volume —
        # an observation makes no precision claim, so these are not pass/fail gates.
        return RuleConfig(
            name=cls.name,
            severity=Severity.INFO,
            params={"cbo_attention": 8, "dit_attention": 4, "noc_attention": 10},
        )

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        cbo_floor = int(config.param("cbo_attention", 8))
        dit_floor = int(config.param("dit_attention", 4))
        noc_floor = int(config.param("noc_attention", 10))
        ck = Structure.over(component).ck()
        if not (ck.cbo > cbo_floor or ck.dit > dit_floor or ck.noc > noc_floor):
            return
        yield Observation(
            rule=self.name,
            component=component.id,
            evidence=Evidence(kind="ck-profile", data=ck.as_dict()),
            message=(
                f"{component.qualname}: "
                f"{ck.narrate(cbo_floor=cbo_floor, dit_floor=dit_floor, noc_floor=noc_floor)}"
            ),
        )
