"""orphans — top-level symbols with no detected references (observation).

Defined at ``{Corpus}``. An orphan is a top-level function/class that nothing in the
corpus appears to reference. That *can* be dead code — but ripgrep and tree-sitter
cannot see dynamic dispatch, reflection, runtime registration, string-keyed lookups,
or callers in other languages / outside the scanned root. So slop cannot honestly
prescribe deletion: a "dead code" verdict here would be a precision claim it cannot
back. This is the canonical emit-evidence-not-verdict case — so orphans is an
``OBSERVATION``: it surfaces the unreferenced symbol (with a confidence derived from
name specificity and language risk) as an investigate-nudge, and the agent decides.

``min_confidence`` (default ``high``) gates the noise. On clean code the high tier is
typically empty; it surfaces only long, specific, genuinely-unreferenced names — the
shape of real dead code an agent leaves behind. The legacy rule was a verdict kept
off-by-default for exactly this noise; as an observation (INFO, never gates) it is safe
to ship enabled.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Evidence, Finding, Observation, Severity
from ..metrics.structural.view import Structure
from ..rule import Rule

_CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}


class OrphansRule(Rule):
    name = "orphans"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # Observation: severity/action are pinned by the type. The only knob is the
        # confidence floor that bounds the noise.
        return RuleConfig(name=cls.name, severity=Severity.INFO, params={"min_confidence": "high"})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        floor = _CONFIDENCE_ORDER.get(str(config.param("min_confidence", "high")), 3)
        for orphan in Structure.over(component).orphans():
            if _CONFIDENCE_ORDER.get(orphan.confidence, 0) < floor:
                continue
            yield Observation(
                rule=self.name,
                component=orphan.locus or component.id,
                line=orphan.line or None,
                evidence=Evidence(
                    kind="orphan",
                    data={"qualname": orphan.qualname, "kind": orphan.kind,
                          "confidence": orphan.confidence},
                ),
                message=(
                    f"{orphan.qualname} ({orphan.kind}) has no detected references "
                    f"[{orphan.confidence} confidence]. Possibly dead code — but confirm it "
                    "is not reached via dynamic dispatch, reflection, registration, or an "
                    "external caller before removing it."
                ),
            )
