"""structure.runts — a package boundary that doesn't earn its weight (verdict).

Defined at ``{Package}``. A runt is a package with exactly one non-init module, no
subpackages, and a trivial ``__init__`` (imports/re-exports only). The namespace
level carries no semantic payload — the lone module could sit flat at the parent
level under the package's name. The fix is singular and mechanical (flatten the
package), so this is a directed ``FLATTEN_PACKAGE`` verdict at WARNING, not a REVIEW.

The topology test lives in the metric (``Structure.is_runt``), keyed on the
per-language package-init convention (``grammar.package_init_name``); languages with
no init-file convention are structurally N/A and never fire.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.view import Structure
from ..rule import Rule


class RuntsRule(Rule):
    name = "structure.runts"
    altitudes = frozenset({ScopeKind.PACKAGE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, severity=Severity.WARNING)

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        if not Structure.over(component).is_runt():
            return
        module = _lone_real_module(component)
        module_name = module.files[0].stem if module and module.files else "its module"
        suggested = f"{component.path.name}.py"
        yield Verdict(
            rule=self.name,
            component=component.id,
            action=Action.FLATTEN_PACKAGE,
            prescription=(
                f"Flatten the runt package {component.qualname}/ into {suggested} at the parent "
                f"level: it wraps a single module ({module_name}) behind a trivial __init__ with "
                "no subpackages, so the namespace level adds no semantic payload."
            ),
            severity=config.severity,
            value=1,
            threshold=1,
            message=f"runt package: single module ({module_name}) behind a trivial __init__",
            metadata={"package": component.qualname, "module": module_name, "suggested": suggested},
        )


def _lone_real_module(package: Scope):
    mods = package.modules()
    grammar = mods[0]._grammar if mods else None
    init_name = grammar.package_init_name() if grammar is not None else None
    reals = [m for m in mods if not (m.files and m.files[0].name == init_name)]
    return reals[0] if reals else None
