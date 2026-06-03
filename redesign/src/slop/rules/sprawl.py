"""lexical.sprawl — a closed alphabet acting as an undeclared type (REVIEW verdict).

When a closed set of values recurs across a naming template — ``_python_extract``,
``_java_extract``, ``_csharp_extract`` — the alphabet (python/java/csharp) is encoding a
type the codebase has not declared. Detection runs token-Levenshtein-1 affix patterns
(Caprile & Tonella 2000), alphabet clustering, and Formal Concept Analysis (Wille 1982;
Ganter & Wille 1999) over the inheritance lattice, file → package → root, claiming each
alphabet at its narrowest coherent scope (``metrics/lexical/affix.sprawl_over``).

Disposition: FCA over identifier names is a structural *hypothesis* — a shared operation
alphabet is suggestive of a missing type, but it can equally be an intentional dispatch
table or plugin family. slop is confident the pattern exists but cannot adjudicate the
remedy, so this is a ``REVIEW`` verdict (which also subsumes the legacy dispatch-family
suppression: a plugin family surfaced as "confirm intent" is the correct outcome).
"""
from __future__ import annotations

import os
from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.lexical import Lexical
from ..metrics.lexical.affix import Lexeme, sprawl_over
from ..rule import Rule


class SprawlRule(Rule):
    name = "lexical.sprawl"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, params={
            "min_alphabet": 3, "min_concept_extent": 2, "min_concept_intent": 2})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_alphabet = int(config.param("min_alphabet", 3))
        min_extent = int(config.param("min_concept_extent", 2))
        min_intent = int(config.param("min_concept_intent", 2))
        root = str(getattr(component, "root", "") or "")

        items: list[Lexeme] = []
        for c in Lexical.over(component).callables():
            if len(c.name) < 2:
                continue
            path = str(c.files[0]) if c.files else ""
            rel = os.path.relpath(path, root) if (path and root) else path
            items.append(Lexeme.of(c.name, file=rel))
        if not items:
            return

        data = sprawl_over(items, min_alphabet=min_alphabet)

        for concept in data.concepts:
            if len(concept.extent) < min_extent or len(concept.intent) < min_intent:
                continue
            entities = ", ".join(sorted(concept.extent))
            ops = ", ".join(sorted(concept.intent))
            yield Verdict(
                rule=self.name, component=component.id, action=Action.REVIEW,
                severity=Severity.WARNING,  # REVIEW caps at WARNING
                prescription=(
                    f"The entities {{{entities}}} share the operation alphabet {{{ops}}} — a "
                    "closed alphabet acting as an undeclared type. Extract a class/enum to make "
                    "the type explicit, or confirm this is an intentional dispatch/plugin family."
                ),
                value=len(concept.extent), threshold=min_extent,
                message=f"closed-alphabet sprawl: {{{entities}}} share {{{ops}}}",
                metadata={"extent": sorted(concept.extent), "intent": sorted(concept.intent),
                          "scope": concept.scope},
            )

        for parent, child in data.inheritance_pairs:
            yield Verdict(
                rule=self.name, component=component.id, action=Action.REVIEW,
                severity=Severity.WARNING,
                prescription=(
                    f"'{child}' operations are a strict superset of '{parent}' — the naming "
                    "template already shows an inheritance the code does not declare. Make it "
                    "explicit with a base type, or confirm the overlap is incidental."
                ),
                value=2, threshold=2,
                message=f"undeclared inheritance: '{child}' extends '{parent}' (by operation alphabet)",
                metadata={"parent": parent, "child": child, "kind": "inheritance_pair"},
            )
