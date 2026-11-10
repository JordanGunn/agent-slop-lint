"""Discovery over the ownership tree.

Answers three questions with facts and no judgment: where is a name defined, what does
a scope hold, which names are defined more than once. Every result is a plain
:class:`Match` carrying the ownership path and a source line, in a deterministic order
(qualname, then path, then line), so two runs over the same tree print the same bytes.

This is the search half of the AST layer. It reads the carved hierarchy; it never
re-parses, thresholds or ranks.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .base import Scope
from .identity import ScopeId, ScopeKind
from ..ast.paradigm import ObjectOriented


@dataclass(frozen=True)
class Match:
    """One scope, reported as a fact: what it is, what it is called, where it lives."""

    kind: ScopeKind
    name: str
    qualname: str
    path: str | None
    line: int | None

    def as_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "qualname": self.qualname,
            "path": self.path,
            "line": self.line,
        }

    def sort_key(self) -> tuple:
        return (self.qualname, self.path or "", self.line or 0)


def walk(scope: Scope) -> Iterator[Scope]:
    """Every scope under ``scope`` (itself included), root-first."""
    yield scope
    for child in scope.children():
        yield from walk(child)


def relative_path(scope_id: ScopeId, root: Path | str) -> str | None:
    """A scope's first source file relative to ``root``, or None if it carries no span.

    Module bare-stem qualnames collide across packages, so the path is what
    disambiguates them."""
    if scope_id.spans and scope_id.spans[0].path:
        try:
            return os.path.relpath(scope_id.spans[0].path, root)
        except ValueError:
            return scope_id.spans[0].path
    return None


class _Lines:
    """1-based line of a byte offset, reading each file once."""

    def __init__(self) -> None:
        self._data: dict[str, bytes | None] = {}

    def of(self, path: str, start_byte: int) -> int | None:
        if path not in self._data:
            try:
                self._data[path] = Path(path).read_bytes()
            except OSError:
                self._data[path] = None
        data = self._data[path]
        if data is None:
            return None
        return data.count(b"\n", 0, start_byte) + 1


def _match(scope: Scope, root: Path | str, lines: _Lines) -> Match:
    span = scope.id.spans[0] if scope.id.spans else None
    return Match(
        kind=scope.id.kind,
        name=scope.name,
        qualname=scope.qualname,
        path=relative_path(scope.id, root),
        line=lines.of(span.path, span.start_byte) if span and span.path else None,
    )


def find(corpus, name: str | None = None, *, kind: ScopeKind | None = None,
         under: Scope | None = None) -> list[Match]:
    """Scopes whose local name is exactly ``name`` (any name when None), optionally of
    one ``kind`` and strictly beneath ``under`` (the whole corpus by default)."""
    start = under if under is not None else corpus
    lines = _Lines()
    found = [
        _match(s, corpus.root, lines)
        for s in walk(start)
        if s is not start
        and (kind is None or s.id.kind is kind)
        and (name is None or s.name == name)
    ]
    return sorted(found, key=Match.sort_key)


def outline(scope: Scope, root: Path | str, *, depth: int | None = None,
            kinds: frozenset[ScopeKind] | None = None) -> list[tuple[int, Match]]:
    """The ownership tree beneath ``scope`` as ``(level, match)`` rows, depth-first,
    siblings ordered by name. ``depth`` limits how many levels below ``scope`` appear;
    ``kinds`` hides other kinds without hiding their children."""
    lines = _Lines()
    rows: list[tuple[int, Match]] = []

    def visit(node: Scope, level: int) -> None:
        if depth is not None and level > depth:
            return
        for child in sorted(node.children(), key=lambda c: (c.name, c.qualname)):
            if kinds is None or child.id.kind in kinds:
                rows.append((level, _match(child, root, lines)))
            visit(child, level + 1)

    visit(scope, 1)
    return rows


def collisions(corpus, *, kind: ScopeKind = ScopeKind.CLASS) -> dict[str, list[Match]]:
    """Names defined by two or more distinct scopes of ``kind``.

    Identity is (qualname, path): module bare-stem qualnames repeat across packages, so
    qualname alone would merge distinct definitions."""
    groups: dict[str, dict[tuple, Match]] = {}
    for match in find(corpus, kind=kind):
        groups.setdefault(match.name, {})[(match.qualname, match.path)] = match
    return {
        name: sorted(by_identity.values(), key=Match.sort_key)
        for name, by_identity in sorted(groups.items())
        if len(by_identity) > 1
    }


def caveats(corpus, kind: ScopeKind | None = None) -> list[str]:
    """Reasons a class-related answer may be incomplete, one line per affected language.

    A realm whose grammar is procedural (C, Julia) carves no class scopes, so its
    ``struct``/type definitions are not discoverable and an empty answer there does not
    mean "not defined". Empty unless the question involves classes (``kind`` is None or
    CLASS)."""
    if kind is not None and kind is not ScopeKind.CLASS:
        return []
    return sorted(
        f"{realm.language}: procedural grammar carves no class scopes; "
        "struct/type definitions are not discovered"
        for realm in corpus.realms()
        if not issubclass(realm.grammar, ObjectOriented)
    )
