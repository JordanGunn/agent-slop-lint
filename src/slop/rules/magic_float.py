"""magic-float: a float with a fractional part used as an operand, without a name.

``x * 9.81`` and ``ratio > 0.7`` are unambiguous: the number means something the reader
must guess (Martin, Clean Code, 2008, G25). Integers are not measured, because syntax
cannot tell a magic ``3`` from a dimension or an offset. See
``metrics/structural/literals.py`` for exactly what counts. The limit is how many uses of
one value are allowed; the default 0 reports every float operand.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..config import RuleConfig
from ..metrics.structural.view import Structure
from ..rule import Rule
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..violation import Violation


class MagicFloatRule(Rule):
    name = "magic-float"
    description = "a float literal is used as an operand more often than the limit allows"
    altitudes = frozenset({ScopeKind.MODULE})

    default_options = {"limit": 0}

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Violation]:
        limit = config.option("limit")
        path = str(component.files[0]) if component.files else None
        for use in Structure.over(component).magic_floats():
            if use.count > limit:
                yield Violation(
                    rule=self.name, path=path, line=use.line, column=use.column,
                    message=f"float {use.value} is an operand {use.count} time(s) in "
                            f"{component.qualname}; name it (limit {limit})",
                    value=use.count, threshold=limit, subject=component.qualname)
