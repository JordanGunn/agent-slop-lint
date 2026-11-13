"""The names a scope declares, as a lexicon.

Lives in the scope layer, above ``slop.lexicon``: it walks the scope tree, takes the
names each scope declares (a package's or module's own name, a class and its properties,
a callable and its parameters), tags each with a lexicon ``Role`` and feeds the plain
``(text, role, span)`` stream to a ``slop.lexicon.Lexicon``.

A project's vocabulary is the names it declares. Names it only refers to (``self``,
``int``, ``np``, a library call) are someone else's words, so they are not counted.
"""
from __future__ import annotations

from typing import Any

from .find import walk
from .identity import ScopeKind
from ..lexicon import Lexicon, Role
from ..span import Span

#: Realm, package and module names come from the filesystem, not from a syntax node.
_FS_ROLE = {
    ScopeKind.REALM: Role.REALM,
    ScopeKind.PACKAGE: Role.PACKAGE,
    ScopeKind.MODULE: Role.MODULE,
}


def _fs_name_unit(comp: Any, role: Role) -> tuple[str, Role, Span]:
    """A filesystem-named scope as a lexicon unit: the name it declares, which for a
    package is its own directory's name (``grammar``, not ``slop/ast/grammar``: the parents
    declare theirs). A fileless name gets an empty path, counted in full and excluded from any
    slice."""
    path = comp.files[0] if comp.files else None
    return comp.name.rsplit("/", 1)[-1], role, Span(str(path) if path is not None else "", 0, 0)


_UNNAMED = frozenset({"<anonymous>", "<lambda>"})


def build_declared_lexicon(scope: Any) -> Lexicon:
    """Build a Lexicon of the names the code *declares*, not every identifier it mentions.

    Modules, packages and realms (from the filesystem), classes, their properties,
    callables and callable parameters, each tagged with its own role. References to
    builtins and libraries (``self``, ``np``, ``int``) are not chosen vocabulary, so they
    are absent; so are unnamed scopes, a grammar's special methods (``__init__``),
    implicit receivers and local variables. Those exclusions are grammar facts, not
    language branches here.

    This is the vocabulary a canonical vocabulary governs: it is chosen where a name is
    declared."""
    units: list[tuple[str, Role, Span]] = []
    for comp in walk(scope):
        units.extend(declared_units(comp))
    return Lexicon(units)


def _is_package_init(comp: Any) -> bool:
    grammar = comp._grammar
    init = grammar.package_init_name() if grammar is not None else None
    return comp.KIND is ScopeKind.MODULE and init is not None and bool(comp.files) and comp.files[0].name == init


def declared_units(comp: Any) -> list[tuple[str, Role, Span]]:
    """The names ``comp`` itself declares (not its children's), each with the role of its kind:
    a module's or package's own name; a class's name and properties; a callable's name and
    parameters. A package's init module (Python's ``__init__.py``) is the package itself, so it
    declares nothing the package does not; a realm is slop's grouping by language, so its name
    (``python``) is not a word the project chose."""
    kind = comp.KIND
    fs_role = _FS_ROLE.get(kind)
    if fs_role is not None:
        return [] if _is_package_init(comp) or kind is ScopeKind.REALM else [_fs_name_unit(comp, fs_role)]
    if kind is ScopeKind.CLASS:
        return _class_units(comp)
    if kind is ScopeKind.CALLABLE:
        return _callable_units(comp)
    return []


def _class_units(comp: Any) -> list[tuple[str, Role, Span]]:
    """A class's own name plus the properties it declares, at the class span."""
    if comp.name in _UNNAMED:
        return []
    span = comp.id.spans[0]
    units = [(comp.name, Role.CLASS, span)]
    units.extend((prop, Role.PROPERTY, span) for prop in comp.properties())
    return units


def _callable_units(comp: Any) -> list[tuple[str, Role, Span]]:
    """A callable's own name unless unnamed or special, plus its parameters other than
    the grammar's implicit receivers, all at the callable span."""
    grammar = comp._grammar
    span = comp.id.spans[0]
    units: list[tuple[str, Role, Span]] = []
    if comp.name not in _UNNAMED and not grammar.is_special_method(comp.name):
        units.append((comp.name, Role.CALLABLE, span))
    receivers = grammar.implicit_receiver_names()
    units.extend((param, Role.PARAMETER, span)
                 for param in comp.parameters() if param not in receivers)
    return units


def _node_holding_nodes(scope: Any):
    """Yield the ``ast.Node`` of each node-holding scope in the extent.
    Node-holding scopes (Module/Class/Callable) own a subtree; aggregates
    recurse to their node-holding descendants, so each file is reached once."""
    if scope._node is not None:
        yield scope._ast_node()
    else:
        for ch in scope.children():
            yield from _node_holding_nodes(ch)

