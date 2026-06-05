"""structure.redundancy — sibling functions sharing project callees (REVIEW verdict).

Defined at ``{Module}``. When two peer top-level functions both call the same set of
project-defined helpers, the module is signalling either a missing shared helper that
should encapsulate the common calls, or a partial copy of one function into the other
(poor factoring). Either way it is worth a look.

Precision (the legacy false-positive this fixes): only *project-defined* shared callees
count — ubiquitous stdlib methods (``.strip``/``.decode``/``.split``) are filtered out by
the metric via the corpus-wide name index, so two functions that merely both call
``.strip()`` are not reported as redundant. ``min_shared`` (default 3) already excludes
single-helper reuse (legitimate DRY).

Disposition: a confident overlap, but the remedy is disjunctive and judgment-bound
(extract a shared helper, merge the two functions, or accept the overlap as
incidental). So this is a ``REVIEW`` verdict, which caps at WARNING — matching the
legacy severity.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.structural.relational import ubiquitous_callees
from ..metrics.structural.view import Structure
from ..rule import Rule


def _ubiquitous(component: Scope, threshold: float) -> frozenset[str]:
    """Corpus-wide ubiquitous-callee set, computed once (walks every function body) and
    memoised on the AnalysisContext, since the rule fires per module."""
    ctx = getattr(component, "context", None)
    key = ("ubiquitous_callees", threshold)
    if ctx is not None and key in ctx.cache:
        return ctx.cache[key]
    root = component
    while getattr(root, "owner", None) is not None:
        root = root.owner
    result = ubiquitous_callees(root, threshold=threshold)
    if ctx is not None:
        ctx.cache[key] = result
    return result


class RedundancyRule(Rule):
    name = "structure.redundancy"
    altitudes = frozenset({ScopeKind.MODULE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        # REVIEW verdict → WARNING-pinned. Knobs: overlap count + overlap fraction, and
        # the document-frequency ceiling above which a project callee is "infrastructure".
        # max_ubiquity calibrated against the v1.2.0 snapshot: genuinely ubiquitous
        # project callees (RuleResult/Violation-style constructors) sit at ~0.07 of all
        # functions; real shared helpers sit at <0.01. 0.05 separates them.
        return RuleConfig(name=cls.name,
                          params={"min_shared": 3, "min_score": 0.5, "max_ubiquity": 0.05})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_shared = int(config.param("min_shared", 3))
        min_score = float(config.param("min_score", 0.5))
        max_ubiquity = float(config.param("max_ubiquity", 0.25))
        exclude = _ubiquitous(component, max_ubiquity)
        pairs = Structure.over(component).redundant_siblings(
            min_shared=min_shared, min_score=min_score, exclude=exclude)
        for pair in pairs:
            shared = ", ".join(pair.shared_callees)
            n = len(pair.shared_callees)
            yield Verdict(
                rule=self.name,
                component=component.id,
                action=Action.REVIEW,
                # REVIEW caps at WARNING structurally (deferred remedy, never gates build).
                severity=Severity.WARNING,
                prescription=(
                    f"'{pair.left}' and '{pair.right}' share {n} project callees ({shared}). "
                    "Extract a shared helper encapsulating the common calls, merge the two "
                    "functions if they are near-copies, or confirm the overlap is incidental."
                ),
                value=n,
                threshold=min_shared,
                message=f"'{pair.left}' and '{pair.right}' share {n} callees: {shared}",
                metadata={"left": pair.left, "right": pair.right,
                          "shared_callees": list(pair.shared_callees)},
            )
