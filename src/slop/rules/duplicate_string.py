"""duplicate-string: one string literal repeated across a module (Sonar S1192).

A string of at least ``min_length`` characters that appears more than ``limit`` times in
a module should be a named constant, so that one edit changes every use. The minimum
length of 5 is Sonar's. Sonar reports at three uses; the default limit here is 4 (five
uses), because at three slop's own source gave 110 findings, mostly idiom (node-type names
repeated across grammar tables, argparse flags), and at five it gave 14.

Precision at the default, every finding classified by hand: in slop's own source 8 of 14 are
real repetition (``"--output"`` x11, ``"utf-8"`` x7) and 6 are node-type names repeated across
grammar tables (``"identifier"``, ruby ``"while"``); in laszy 9 of 9 are real. No exemption
for tables is added: a repeated name in a table is subjective, so a project with such tables
raises ``limit`` or excludes them. See ``metrics/structural/literals.py`` for what is not
counted.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..config import RuleConfig
from ..metrics.structural.view import Structure
from ..rule import Rule
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..violation import Violation


class DuplicateStringRule(Rule):
    name = "duplicate-string"
    description = "a string literal is repeated in a module more often than the limit allows"
    altitudes = frozenset({ScopeKind.MODULE})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, enabled=True, options={"limit": 4, "min_length": 5})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Violation]:
        limit = config.option("limit")
        path = str(component.files[0]) if component.files else None
        for use in Structure.over(component).repeated_strings(min_length=config.option("min_length")):
            if use.count > limit:
                yield Violation(
                    rule=self.name, path=path, line=use.line, column=use.column,
                    message=f"string {use.value} appears {use.count} times in "
                            f"{component.qualname}; name it (limit {limit})",
                    value=use.count, threshold=limit, subject=component.qualname)
