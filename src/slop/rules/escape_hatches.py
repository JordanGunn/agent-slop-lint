"""structure.escape-hatches — escape-hatch type-annotation density (verdict).

Defined at ``{Module}``. Flags a module where a significant fraction of its type
annotations use the language's escape-hatch type (Python ``Any``, TS ``any``, Go
``any``/``interface{}``, Java ``Object``, C# ``object``/``dynamic``, Rust ``dyn
Any``, Julia ``Any``). High escape-hatch density is systemic type-evasion — the
annotations are present but carry no information — which is structural debt, not a
style nit an agent self-corrects.

The remedy is non-disjunctive (replace the escape-hatch annotations with specific
types), so this is an ordinary corrective verdict, not a REVIEW. A ``min_annotations``
noise floor keeps thinly-annotated modules quiet; that gates output volume, not the
claim. Threshold (0.30) and floor (5) are the legacy shipped defaults.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class EscapeHatchesRule(Rule):
    name = "structure.escape-hatches"
    altitudes = frozenset({ScopeKind.MODULE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.WARNING,
            thresholds={ScopeKind.MODULE.value: 0.30},  # > 30% of annotations
            params={"min_annotations": 5},
        )

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        threshold = config.threshold_for(component.id.kind)
        if threshold is None:
            return
        escapes, total = Structure.over(component).escape_hatch_counts()
        min_annotations = int(config.param("min_annotations", 5))
        if total < min_annotations:
            return
        density = escapes / total if total else 0.0
        if density <= threshold:
            return
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.REPLACE_ESCAPE_TYPE,
            prescription=(
                f"Replace escape-hatch annotations in {component.qualname} with specific "
                f"types: {escapes}/{total} annotations ({density * 100:.0f}%) are dynamic/Any "
                f"and carry no type information."
            ),
            severity=config.severity,
            value=round(density, 4),
            threshold=threshold,
            message=f"{density * 100:.1f}% of type annotations are escape-hatch types ({escapes}/{total})",
        )
