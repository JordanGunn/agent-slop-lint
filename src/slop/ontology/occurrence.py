"""Where a vocabulary word reaches the code, and the plan to replace it.

``occurrences`` lists every declared name (module, package, class, callable, parameter,
property) whose identifier contains a word. ``rename`` plans the text edits that replace
that word with another in those names and in the references to them. Both are fact lists
over the corpus; nothing is written to any file.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from ..ast.binding import SymbolKind
from ..lexicon import Role, plural, split_tokens, stem
from ..scope.find import walk
from ..scope.identity import ScopeKind
from ..scope.lexicon import declared_units

#: names whose file or directory is the declaration: renaming them is not a text edit
_FILES = frozenset({Role.MODULE, Role.PACKAGE})
#: names that only their own declaration's file can refer to
_LOCAL = frozenset({Role.PROPERTY, Role.PARAMETER})
#: what a binding is when it names a declaration of another file
_IMPORTED = frozenset({SymbolKind.FREE, SymbolKind.IMPORT})
#: what a property's or parameter's own definition binds as
_DEFINED_AS = {Role.PROPERTY: SymbolKind.FIELD, Role.PARAMETER: SymbolKind.PARAMETER}


@dataclass(frozen=True)
class Occurrence:
    """One declared name containing a word: the identifier as written, its role, the absolute
    path and 1-based line of its declaration, and the qualname of the scope it belongs to (the
    enclosing scope for a module, package, class or callable; the owner for a parameter or
    property)."""

    identifier: str
    role: str
    path: str
    line: int
    scope: str


@dataclass(frozen=True)
class Edit:
    """Replace ``before`` by ``after`` at the 1-based ``line`` and ``column`` (in characters)
    of the file at ``path``."""

    path: str
    line: int
    column: int
    before: str
    after: str


@dataclass(frozen=True)
class _Declaration:
    """A declared name with where it is written: the byte its definition starts at, if known."""

    identifier: str
    role: Role
    path: Path
    content: bytes
    start: int | None
    line: int
    scope: str


def occurrences(word: str, corpus: Any) -> tuple[Occurrence, ...]:
    """Every declared name in ``corpus`` whose identifier has ``word`` as a token (case-insensitive),
    in path then line order."""
    found = [Occurrence(d.identifier, d.role.value, str(d.path), d.line, d.scope)
             for d in _declarations(corpus) if _has_word(d.identifier, word)]
    return tuple(sorted(found, key=lambda o: (o.path, o.line, o.identifier, o.role)))


def rename(old: str, new: str, corpus: Any) -> tuple[Edit, ...]:
    """The edits that replace the word ``old`` with ``new`` in every declared name containing it
    and in every reference to those declarations.

    References are the occurrences in the declaring file that bind to the declaration, plus, for
    a class, callable, module or package, the occurrences of the same name in other files that
    bind to an import or to nothing in their own file (which is how another module reaches it).
    A parameter or property is only referred to in its own file. The file or directory that a
    module or package name comes from is not text, so renaming it is not an edit in the plan;
    only the references to it are. The new spelling keeps the case style of the word it
    replaces. Edits are sorted by path, line and column, without duplicates."""
    modules = {m.path: m for m in _modules(corpus)}
    edits: set[Edit] = set()
    for decl in _declarations(corpus):
        if _has_word(decl.identifier, old):
            home = None if decl.role in _FILES else modules.get(str(decl.path))
            edits |= _home_edits(decl, home, old, new)
            if decl.role not in _LOCAL:
                edits |= _importer_edits(decl, modules, home, old, new)
    return tuple(sorted(edits, key=lambda e: (e.path, e.line, e.column)))


def _home_edits(decl: _Declaration, home: _Module | None, old: str, new: str) -> set[Edit]:
    """The declaration itself and what binds to it in its own file."""
    if home is None or decl.start is None:
        return set()
    return {_edit(home, b.start, b.text, old, new) for b in home.bindings
            if b.start == decl.start or b.definition == decl.start}


def _importer_edits(decl: _Declaration, modules: dict[str, _Module], home: _Module | None,
                    old: str, new: str) -> set[Edit]:
    """Occurrences of the name in other files that bind to an import or to nothing there."""
    return {_edit(other, b.start, b.text, old, new) for path, other in modules.items()
            if other is not home and path != str(decl.path)
            for b in other.bindings if b.text == decl.identifier and b.kind in _IMPORTED}


# ---- spelling -------------------------------------------------------------------------

def _has_word(identifier: str, word: str) -> bool:
    """``identifier`` contains ``word`` or an inflection of it."""
    return stem(word) in (stem(t) for t in split_tokens(identifier))


def _respell(identifier: str, old: str, new: str) -> str:
    """``identifier`` with each token that is ``old`` or an inflection of it replaced by ``new``
    in that token's case style. A token that adds an ``-s`` to ``old`` (``nodes`` for ``node``)
    gets the plural of ``new``; any other inflection gets ``new`` as given."""
    out, cursor, copied = [], 0, 0
    for token in split_tokens(identifier):
        at = identifier.index(token, cursor)
        cursor = at + len(token)
        if stem(token) != stem(old):
            continue
        plural_form = token.lower() != old.lower() and token.lower().endswith("s") and not old.lower().endswith("s")
        out.append(identifier[copied:at])
        out.append(_styled(plural(new) if plural_form else new, token, identifier))
        copied = cursor
    out.append(identifier[copied:])
    return "".join(out)


def _styled(word: str, token: str, identifier: str) -> str:
    """``word`` in the style of ``token``: UPPER, Capitalized or lower."""
    word = word.lower()
    if token.isupper() and (len(token) > 1 or not any(c.islower() for c in identifier)):
        return word.upper()
    if token[0].isupper():
        return word.capitalize()
    return word


# ---- corpus walk ----------------------------------------------------------------------

@dataclass(frozen=True)
class _Module:
    path: str
    content: bytes
    bindings: tuple

    def position(self, offset: int) -> tuple[int, int]:
        """The 1-based line and character column of byte ``offset``."""
        line_start = self.content.rfind(b"\n", 0, offset) + 1
        line = self.content.count(b"\n", 0, offset) + 1
        return line, len(self.content[line_start:offset].decode("utf-8", errors="replace")) + 1


def _edit(module: _Module, offset: int, text: str, old: str, new: str) -> Edit:
    line, column = module.position(offset)
    return Edit(module.path, line, column, text, _respell(text, old, new))


def _modules(corpus: Any) -> Iterator[_Module]:
    for comp in walk(corpus):
        if comp.KIND is ScopeKind.MODULE and comp._node is not None and comp.files:
            yield _Module(str(Path(comp.files[0]).absolute()), comp._content,
                          tuple(sorted(comp.bindings().values(), key=lambda b: b.start)))


def _declarations(corpus: Any) -> Iterator[_Declaration]:
    """Every name the corpus declares (``slop.scope.lexicon.declared_units``), with where it is written."""
    for comp in walk(corpus):
        for name, role, _span in declared_units(comp):
            yield _declaration(comp, name, role)


def _declaration(comp: Any, name: str, role: Role) -> _Declaration:
    owner = comp.owner.id.qualname if comp.owner is not None else ""
    if role in _FILES:
        path = comp.path if role is Role.PACKAGE else comp.files[0]
        return _Declaration(name, role, Path(path).absolute(), b"", None, 1, owner)
    bindings = comp.bindings()
    if role in _DEFINED_AS:
        kind = _DEFINED_AS[role]
        return _named(comp, name, role, _first(bindings, name, comp._node, lambda b: b.kind is kind), comp.id.qualname)
    return _named(comp, name, role, _name_start(comp, bindings), owner)


def _name_start(comp: Any, bindings: dict) -> int | None:
    """The byte where the declaration's own name is written: its ``name`` field, else the first
    defining occurrence of that name inside the declaration."""
    named = comp._node.child_by_field_name("name")
    if named is not None and named.start_byte in bindings:
        return named.start_byte
    return _first(bindings, comp.name, comp._node, lambda b: True)


def _first(bindings: dict, text: str, node: Any, accept: Any) -> int | None:
    for start in sorted(bindings):
        b = bindings[start]
        if b.defines and b.text == text and node.start_byte <= start < node.end_byte and accept(b):
            return start
    return None


def _named(comp: Any, identifier: str, role: Role, start: int | None, scope: str) -> _Declaration:
    module = comp
    while module.KIND is not ScopeKind.MODULE and module.owner is not None:
        module = module.owner
    path = Path(comp.files[0]).absolute() if comp.files else Path("")
    content = module._content
    line = content.count(b"\n", 0, start) + 1 if start is not None else comp.line
    return _Declaration(identifier, role, path, content, start, line, scope)
