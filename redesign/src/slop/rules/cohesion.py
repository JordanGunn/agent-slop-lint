"""lexical.cohesion — a module whose vocabulary is foreign to its package (observation).

Sibling modules of one package are about one thing, so they share vocabulary. A module
that shares almost none of its identifier vocabulary with the rest of its package is a
*foreign body* — code that does not talk about what its container talks about (an
infrastructure helper filed under a domain package, or a module that has drifted from
its home).

Measured as the Jaccard overlap of the module's cleaned identifier token-set against the
union of the rest of its package — a ``Selection`` of the package's other children
(``lexicon.jaccard`` over the two token spaces; ``js_similarity`` reported alongside as
the distribution-aware second opinion). The affinity probe validated the signal on the
v1.2.0 snapshot: module-vs-package overlap medians ~0.19, while pure-infrastructure
modules sit far below (find/grep ~0.0, color ~0.04) — and the signal retro-predicts v3's
own relocation of those exact modules.

Disposition (per the disposition policy): an ``OBSERVATION``. The cohesion score is an
exact measurement, but its remedy is open and uncertain — a low-cohesion module may be
genuinely misplaced, or a legitimately cross-cutting utility that belongs where it is.
slop surfaces the evidence; the agent decides whether to relocate. Never a directive
verdict (and never a build gate).

Significance gates (noise floors from the probe): single-child packages (no rest-of-
package to compare against), ``__init__``, and modules below ``min_tokens`` (default 8)
distinct identifiers are skipped; a module surfaces only when its cohesion is below
``max_cohesion`` (default 0.10 — well under the ~0.19 baseline, catching the clear
foreign bodies without flagging the ordinary tail).
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..scope.lexicon import build_lexicon
from ..scope.selection import Selection
from ..config import RuleConfig
from ..finding import Evidence, Finding, Observation
from ..lexicon import jaccard, js_similarity
from ..rule import Rule


class CohesionRule(Rule):
    name = "lexical.cohesion"
    altitudes = frozenset({ScopeKind.MODULE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, params={"max_cohesion": 0.10, "min_tokens": 8})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        max_cohesion = float(config.param("max_cohesion", 0.10))
        min_tokens = int(config.param("min_tokens", 8))

        if component.name == "__init__":
            return
        package = component.owner
        if package is None:
            return
        siblings = [c for c in package.children() if c is not component]
        if not siblings:
            return  # single-child package: no rest-of-package to compare against

        module_lex = component.lexicon()
        if module_lex.significant_token_count() < min_tokens:
            return
        module_freq = module_lex.frequencies()
        context_freq = build_lexicon(Selection(siblings)).frequencies()
        if not context_freq:
            return

        score = jaccard(module_freq, context_freq)
        if score >= max_cohesion:
            return
        js = js_similarity(module_freq, context_freq)
        shared = sorted(set(module_freq) & set(context_freq))
        yield Observation(
            rule=self.name,
            component=component.id,
            evidence=Evidence(kind="vocabulary-cohesion", data={
                "cohesion": round(score, 4),
                "js_similarity": round(js, 4),
                "package": package.qualname,
                "module_tokens": module_lex.significant_token_count(),
                "shared_tokens": shared[:15],
            }),
            message=(
                f"module '{component.name}' shares only {score:.0%} of its vocabulary with the "
                f"rest of package '{package.qualname}' — a possible foreign body. Its identifiers "
                "are about something its package mates are not; consider whether it belongs here "
                "or should move closer to the code it resembles."
            ),
            metadata={"cohesion": round(score, 4), "package": package.qualname},
        )
