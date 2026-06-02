"""vocabulary — identifier token distribution (observation).

Defined at ``{Package}``. Emits a claim-free observation, never a verdict: the
identifier token distribution is a Zipf near-invariant (α≈0.9, hapax≈0.49
regardless of discipline), so no scalar threshold is honest. The rule surfaces the
empirical object and lets the consuming agent judge whether the head/tail shape
deviates from the package's domain. A noise floor (``package_min_distinct``) keeps
trivial packages quiet — that gates output volume, not the claim.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..component.base import Component
from ..config import RuleConfig
from ..component.identity import ComponentKind
from ..finding import Evidence, Finding, Observation, Severity
from ..rule import Rule


class TokenDistributionRule(Rule):
    name = "vocabulary"
    altitudes = frozenset({ComponentKind.PACKAGE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name,
            severity=Severity.INFO,
            params={"package_min_distinct": 40, "top_tokens": 15},
        )

    def check(self, component: Component, config: RuleConfig) -> Iterable[Finding]:
        lexicon = component.lexicon()
        distinct = lexicon.significant_token_count()
        floor = int(config.param("package_min_distinct", 40))
        if distinct < floor:
            return
        top_n = int(config.param("top_tokens", 15))
        dist = lexicon.distribution(top=top_n)
        yield Observation(
            rule=self.name,
            component=component.id,
            evidence=Evidence(kind="token-distribution", data=dist.as_dict()),
            message=f"{component.qualname}: {dist.narrate()}",
        )
