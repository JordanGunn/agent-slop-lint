"""homonym: one class name defined more than once in a language (an overloaded word).

A word that names two classes asks every reader, person or agent, which one is meant. The
measure is the one `slop find --collisions` reports for classes; private names (a leading
underscore) are implementation detail and are left out. Whether two definitions are one
concept spelled twice, variants a namespace tells apart, or two meanings sharing a word is
judgement, so the rule is subjective.

Measured (2026-11, by hand): on slop's own source 6 of 7 such names are aliased where a module
needs both (``Corpus as CorpusABC``), and the seventh is a protocol beside its implementation;
on laszy 7 of 12 are aliased somewhere. An alias is the clash surfacing at a use site.

The residue's span and fingerprint cover the first definition only, so editing another
definition does not make a ruling stale.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..config import RuleConfig
from ..rule import Rule
from ..scope.base import Scope
from ..scope.find import collisions, locate
from ..scope.identity import ScopeKind
from ..violation import Violation


class HomonymRule(Rule):
    name = "homonym"
    description = "one class name is defined more than once in a language (an overloaded word)"
    altitudes = frozenset({ScopeKind.CORPUS})
    subjective = True       # one concept twice, variants a namespace tells apart, or two meanings: judgement

    default_options = {"limit": 1}

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Violation]:
        limit = config.option("limit")
        groups = {name: matches for name, matches in collisions(component, kind=ScopeKind.CLASS).items()
                  if not name.startswith("_") and len(matches) > limit}
        if not groups:
            return
        located = {(m.qualname, m.path): scope for scope, m in locate(component._iter_classes(), component.root)}
        for name, matches in groups.items():
            where = "; ".join(f"{m.path}:{m.line} {m.qualname}" for m in matches)
            first = located[(matches[0].qualname, matches[0].path)]
            others = tuple(located[(m.qualname, m.path)].id for m in matches[1:])
            yield Violation.at(first, self.name, f"class name '{name}' is defined {len(matches)} times: {where}",
                               value=len(matches), threshold=limit, related=others)
