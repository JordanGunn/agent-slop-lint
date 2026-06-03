"""hotspots — churn x complexity refactoring-priority signal (observation).

Defined at ``{Corpus}``. Tornhill (2015): the files worth refactoring first are the
ones that are both *complex* (hard to change safely) and *churning* (changed often) —
their product is where review effort has the most leverage. slop joins per-file
cyclomatic complexity with git churn (LOC delta over a 14-day window, the agentic-era
proxy) and classifies each file into a quadrant.

This is a *prioritisation* signal, not a defect: a high-churn/high-complexity file is
not itself wrong (it is often the legitimately load-bearing core), and the measure is
git-dependent (no history → no signal). There is no honest scalar verdict here. So
hotspots is an ``OBSERVATION`` — it surfaces the leverage points (the ``hotspot``
quadrant only; calm/churning-simple/stable-complex are context) as investigate-nudges,
and the agent decides where to spend effort. Silent off-git (the metric returns []).
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Evidence, Finding, Observation
from ..metrics.structural.view import Structure
from ..rule import Rule


class HotspotsRule(Rule):
    name = "hotspots"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # Observation: severity/action pinned. The window is the only knob.
        return RuleConfig(name=cls.name, params={"since": "14 days ago"})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        since = str(config.param("since", "14 days ago"))
        for h in Structure.over(component).hotspots(since=since):
            if h.quadrant != "hotspot":
                continue
            yield Observation(
                rule=self.name,
                component=component.id,
                evidence=Evidence(
                    kind="hotspot",
                    data={"path": h.path, "churn": h.churn,
                          "complexity": h.complexity, "quadrant": h.quadrant},
                ),
                message=(
                    f"{h.path} is a hotspot: complexity {h.complexity} x churn {h.churn} "
                    f"(LOC delta, {since}). High-churn + high-complexity — refactoring here "
                    "has the most leverage. Prioritise reviewing/simplifying it."
                ),
            )
