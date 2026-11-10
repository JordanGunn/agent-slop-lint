"""Violation: one rule broken at one source location.

This is everything a rule reports, and deliberately no more, as in flake8, ruff or pylint:
which rule, where (``path:line:column``), and one factual message. A rule that measures
something also records the ``value`` it measured and the ``threshold`` it exceeded, so a
reader sees the numbers without parsing the message. A violation does not advise, rank,
or say how sure it is: deciding what a violation *means* is judgement, and judgement is
a separate layer from checking.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scope.identity import ScopeKind


@dataclass(frozen=True)
class Violation:
    #: The rule's name (``cyclomatic-complexity``), the one identifier used in config,
    #: in ``slop check`` and in an inline ``slop: ignore[...]`` comment.
    rule: str
    #: Absolute path of the source file (or package directory), None when there is none.
    path: str | None
    #: 1-based line and column of the construct the violation is about.
    line: int
    column: int
    message: str
    value: float | int | None = None
    threshold: float | int | None = None

    @classmethod
    def at(cls, scope: Any, rule: str, message: str, *,
           value: float | int | None = None, threshold: float | int | None = None) -> Violation:
        """A violation located at the definition of ``scope``: a module, class or callable
        (its first source line), or a package (its directory)."""
        node = getattr(scope, "_node", None)
        point = getattr(node, "start_point", None)
        files = scope.files
        if files and scope.id.kind is ScopeKind.PACKAGE:
            path: str | None = str(Path(files[0]).parent)
        else:
            path = str(files[0]) if files else None
        return cls(
            rule=rule,
            path=path,
            line=point[0] + 1 if point is not None else 1,
            column=point[1] + 1 if point is not None else 1,
            message=message,
            value=value,
            threshold=threshold,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
        }
