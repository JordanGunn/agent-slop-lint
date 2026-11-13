"""Discovery over the ownership tree.

Answers three questions with facts and no judgment: where is a name defined, what does
a scope hold, which names are defined more than once. Every result is a plain
:class:`Match` carrying the ownership path and a source line, in a deterministic order
(qualname, then path, then line), so two runs over the same tree print the same bytes.

This is the search half of the AST layer. It reads the carved hierarchy; it never
re-parses, thresholds or ranks.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .model import Scope
from .identity import ScopeKind
from ..identity import relative_path
from ..ast.paradigm import ObjectOriented


@dataclass(frozen=True)
class Match:
    """One scope, reported as a fact: what it is, what it is called, where it lives."""

    kind: ScopeKind
    name: str
    qualname: str
    path: str | None
    line: int | None
    language: str | None = None

    def as_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "qualname": self.qualname,
            "path": self.path,
            "line": self.line,
            "language": self.language,
        }

    def sort_key(self) -> tuple:
        return (self.qualname, self.path or "", self.line or 0)


def walk(scope: Scope) -> Iterator[Scope]:
    """Every scope under ``scope`` (itself included), root-first."""
    yield scope
    for child in scope.children():
        yield from walk(child)


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


def _language_of(scope: Scope) -> str | None:
    """The language of the realm that is, or encloses, ``scope`` (None for the corpus)."""
    node: Scope | None = scope
    while node is not None and node.id.kind is not ScopeKind.REALM:
        node = node.owner
    return node.language if node is not None else None


def _match(scope: Scope, root: Path | str, lines: _Lines) -> Match:
    span = scope.id.spans[0] if scope.id.spans else None
    return Match(
        kind=scope.id.kind,
        name=scope.name,
        qualname=scope.qualname,
        path=relative_path(scope.id, root),
        line=lines.of(span.path, span.start_byte) if span and span.path else None,
        language=_language_of(scope),
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


def locate(scopes: Iterable[Scope], root: Path | str) -> list[tuple[Scope, Match]]:
    """Each of ``scopes`` paired with where it is defined, in :class:`Match` order, for
    callers that need the component as well as the fact (a measure over each class)."""
    lines = _Lines()
    located = [(s, _match(s, root, lines)) for s in scopes]
    return sorted(located, key=lambda pair: pair[1].sort_key())


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


_UNNAMED = "<anonymous>"


def collisions(corpus, *, kind: ScopeKind = ScopeKind.CLASS) -> dict[str, list[Match]]:
    """Names defined by two or more distinct scopes of ``kind`` within one language.

    A name defined once in Python and once in TypeScript is not a collision: the two are
    usually one concept mirrored across a language boundary, and one grammar's scopes cannot
    shadow another's. Two definitions inside one language are, and the entry for that name
    lists every definition in each language that has such a clash (each match says which).

    Identity is (qualname, path): module bare-stem qualnames repeat across packages, so
    qualname alone would merge distinct definitions. Unnamed scopes are not collisions."""
    groups: dict[tuple[str | None, str], dict[tuple, Match]] = {}
    for match in find(corpus, kind=kind):
        if match.name == _UNNAMED:
            continue
        groups.setdefault((match.language, match.name), {})[(match.qualname, match.path)] = match
    clashing: dict[str, list[Match]] = {}
    for (_language, name), by_identity in groups.items():
        if len(by_identity) > 1:
            clashing.setdefault(name, []).extend(by_identity.values())
    return {name: sorted(matches, key=Match.sort_key) for name, matches in sorted(clashing.items())}


def _realms_under(corpus, scope: Scope) -> list:
    """The realms a question about ``scope`` can touch: all of them for the corpus, else
    the realm that is, or encloses, ``scope``."""
    if scope is corpus:
        return list(corpus.realms())
    node = scope
    while node is not None and node.id.kind is not ScopeKind.REALM:
        node = node.owner
    return [node] if node is not None else []


def caveats(corpus, kind: ScopeKind | None = None, *, under: Scope | None = None) -> list[str]:
    """Reasons an answer about ``under`` (the whole corpus by default) may be incomplete.

    - A realm whose grammar is procedural-only carves no class scopes, so its type
      definitions are not discoverable and an empty class answer there does not mean "not
      defined". No shipped grammar is procedural-only today (C and Julia carve their
      struct/abstract types); the guard keeps a future one honest. Reported only for
      questions about classes (``kind`` None or CLASS).
    - A file with syntax errors is still carved, but definitions inside the broken region
      may be missing, for any kind of question.

    Only realms and files that ``under`` actually contains are reported."""
    target = under if under is not None else corpus
    notes: list[str] = []
    if kind is None or kind is ScopeKind.CLASS:
        notes.extend(
            f"{realm.language}: procedural grammar carves no class scopes; "
            "struct/type definitions are not discovered"
            for realm in _realms_under(corpus, target)
            if not issubclass(realm.grammar, ObjectOriented)
        )
    broken = sorted(
        relative_path(m.id, corpus.root) or m.qualname
        for m in walk(target)
        if m.id.kind is ScopeKind.MODULE and m._ast_node().raw.has_error
    )
    if broken:
        shown = ", ".join(broken[:5]) + (f", and {len(broken) - 5} more" if len(broken) > 5 else "")
        notes.append(f"{len(broken)} file(s) have syntax errors, so definitions in them "
                     f"may be missing: {shown}")
    return sorted(notes)
