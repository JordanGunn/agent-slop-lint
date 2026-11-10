"""magic-literal: numeric literals used as operands without a name (Martin 2008, G25).

The measure is the number of distinct numeric literals in a callable that are operands
of an operator (``x > 15``, ``x * 86400``), excluding 0, 1 and 2. See
``metrics/structural/callable_measures.py`` for exactly what counts. The default limit of
0 reports every one, as ESLint ``no-magic-numbers`` and pylint ``magic-value-comparison``
do. Bitwise and shift operands are reported too: in packing code a mask is a format
definition, so raise ``limit`` or exclude that code rather than expect an exemption.
"""
from __future__ import annotations

from ..metrics.structural.view import Structure
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from .limit import Limit


class MagicLiteralRule(Limit):
    name = "magic-literal"
    description = "a callable uses more unnamed numeric literals as operands than the limit"
    altitude = ScopeKind.CALLABLE
    default_limit = 0

    def measure(self, view: Structure) -> int:
        return len(view.magic_literals())

    def describe(self, component: Scope, value: int, limit: float, view: Structure) -> str:
        shown = ", ".join(m.value for m in view.magic_literals())
        return f"{component.qualname} uses {value} unnamed numeric literal(s): {shown} (limit {limit})"
