"""Violation: one rule broken at one source location.

This is everything a rule reports, and deliberately no more, as in flake8, ruff or pylint:
which rule, where (``path:line:column``), and one factual message. A rule that measures
something also records the ``value`` it measured and the ``threshold`` it exceeded, and every
violation records the ``scope`` it is about and the ``related`` scopes it names (the other
clones, the other definitions, the rest of a cycle), so a reader or a later layer sees the
numbers and the structure without parsing the message. A violation does not advise, rank,
or say how sure it is: deciding what a violation *means* is judgement, and judgement is
a separate layer from checking.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .identity import ScopeId, project_path
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
    #: Qualified name of the class, callable, module or package the violation is about.
    subject: str | None = None
    #: Identity of that class, callable, module or package (qualnames can repeat; this cannot).
    scope: ScopeId | None = None
    #: The other scopes the violation names, in the order the message names them.
    related: tuple[ScopeId, ...] = ()
    #: What tells this violation apart from the rule's others about the same subject (the
    #: repeated string, the float), for rules that report several per subject; else None.
    key: str | None = None

    @classmethod
    def at(cls, scope: Any, rule: str, message: str, *, value: float | int | None = None,
           threshold: float | int | None = None, related: tuple[ScopeId, ...] = ()) -> Violation:
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
            subject=scope.qualname,
            scope=scope.id,
            related=related,
        )

    def id(self, root: Path) -> str:
        """A stable id: the rule, the file relative to the project ``root``, the subject and the
        key, not the line, so it survives edits that move the finding."""
        return finding_id(self.rule, project_path(self.path, root) if self.path else "", self.subject or "", self.key)

    @property
    def position(self) -> tuple[str, int, int, str]:
        """Where the violation is, as a sort key: path, line, column, rule."""
        return (self.path or "", self.line, self.column, self.rule)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "subject": self.subject,
            "scope": scope_json(self.scope),
            "related": [scope_json(r) for r in self.related],
        }


_ID_LENGTH = 16


def finding_id(rule: str, path: str, subject: str, key: str | None = None) -> str:
    """The id of the finding of ``rule`` about ``subject`` in ``path``, told apart by ``key``. An
    id without a key is the digest of the first three alone, so it never changes for rules
    that report one finding per subject."""
    fields = (rule, path, subject) if key is None else (rule, path, subject, key)
    return hashlib.sha256("\0".join(fields).encode("utf-8")).hexdigest()[:_ID_LENGTH]


def scope_json(scope: ScopeId | None) -> dict[str, Any] | None:
    """A scope as JSON: its kind, qualified name, and the file it is in."""
    if scope is None:
        return None
    return {"kind": scope.kind.value, "qualname": scope.qualname,
            "path": scope.spans[0].path if scope.spans else None}
