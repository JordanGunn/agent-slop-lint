"""structure.sentinels — stringly-typed sentinel parameters (verdict).

Defined at ``{Callable}``. A parameter named like a closed set of options
(``status``, ``mode``, ``kind``, ``level``, ``format``, …) and typed as a bare
string forces every caller to recall a magic constant from memory or docs, and
defeats exhaustiveness checking. The fix is singular and mechanical — replace the
string type with a ``Literal[...]`` or an ``Enum`` — so this is a directed-corrective
verdict (``REPLACE_SENTINEL_TYPE``) at WARNING, one finding per offending parameter.

The metric layer reports the *fact* (a sentinel-named, string-typed parameter); the
SENTINEL_NAMES vocabulary and the rule's threshold live below it. v3 does not yet
collect call-site literal cardinality (``observed_literals`` is plumbed but empty), so
this flags by name+type alone; surfacing the observed values is a future enrichment.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class SentinelsRule(Rule):
    name = "structure.sentinels"
    altitudes = frozenset({ScopeKind.CALLABLE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, severity=Severity.WARNING)

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        for sentinel in Structure.over(component).sentinel_parameters():
            observed = ""
            if sentinel.observed_literals:
                preview = ", ".join(f'"{v}"' for v in sentinel.observed_literals[:5])
                observed = f" (call-site values: {preview})"
            yield Verdict(
                rule=self.name,
                component=component.id,
                action=Action.REPLACE_SENTINEL_TYPE,
                prescription=(
                    f"Type parameter '{sentinel.name}' of {component.qualname} as a "
                    f"Literal[...] or Enum instead of a bare string{observed}. Callers "
                    "then get the valid values from the type, and exhaustiveness is checkable."
                ),
                severity=config.severity,
                message=f"parameter '{sentinel.name}' is stringly-typed — should be a Literal/Enum",
                metadata={"parameter": sentinel.name, "observed_literals": list(sentinel.observed_literals)},
            )
