"""The component -> lexicon bridge.

Lives in the component/model layer — *above* both ``slop.ast`` and ``slop.lexicon``
— because it is the one place allowed to know both: it pulls identifier tokens from
the AST proxy, tags each with a lexicon ``Role``, unions the filesystem-derived
component names, and feeds the plain ``(text, role, span)`` stream to a
``slop.lexicon.Lexicon``. Neither bottom-layer package imports the other; this bridge
is what wires them.

``slop.ast`` yields identifiers *as written* (``Node.identifiers()``); the lexicon
decides what counts as vocabulary (tokenise/lowercase/strip). The split is the clean
seam between the two.

Role assignment is coarse by design for now (see ``slop.lexicon.roles``): fs names ->
``REALM``/``PACKAGE``/``MODULE``; every AST identifier -> ``BODY_REF``. The finer
``CLASS``/``CALLABLE``/``PARAMETER`` partition is wired when a rule first needs it.
"""
from __future__ import annotations

from typing import Any

from .identity import ScopeKind
from ..lexicon import Lexicon, Role
from ..span import Span

#: Filesystem-derived component names carry the grammatical-degradation signal
#: (module/package names come from the directory tree, not an AST node).
_FS_ROLE = {
    ScopeKind.REALM: Role.REALM,
    ScopeKind.PACKAGE: Role.PACKAGE,
    ScopeKind.MODULE: Role.MODULE,
}


def build_lexicon(component: Any) -> Lexicon:
    """Build a Lexicon over a component: AST identifiers ∪ fs-derived names.

    Identifier tokens come from the ``slop.ast`` proxy via ``Node.identifiers()``
    (the AST's own ``NodeKind.IDENTIFIER`` classification, walked over each
    node-holding component in the extent), tagged ``BODY_REF``. Module/package/realm
    names come from the filesystem, tagged with their kind's role; a fileless name
    gets an empty path (counted in full, excluded from any slice)."""
    units: list[tuple[str, Role, Span]] = []
    for node in _node_holding_nodes(component):
        for text, span in node.identifiers():
            units.append((text, Role.BODY_REF, span))
    for comp in _iter_all(component):
        role = _FS_ROLE.get(comp.KIND)
        if role is not None:
            path = comp.files[0] if comp.files else None
            units.append((comp.name, role, Span(str(path) if path is not None else "", 0, 0)))
    return Lexicon(units)


_UNNAMED = frozenset({"<anonymous>", "<lambda>"})


def build_declared_lexicon(component: Any) -> Lexicon:
    """Build a Lexicon of the names the code *declares*, not every identifier it mentions.

    Modules, packages and realms (from the filesystem), classes, their properties,
    callables and callable parameters, each tagged with its own role. References to
    builtins and libraries (``self``, ``np``, ``int``) are not chosen vocabulary, so they
    are absent; so are unnamed scopes, a grammar's special methods (``__init__``),
    implicit receivers and local variables. Those exclusions are grammar facts, not
    language branches here.

    This is the vocabulary a canonical vocabulary governs: it is chosen where a name is
    declared. ``build_lexicon`` keeps the undifferentiated occurrence stream."""
    units: list[tuple[str, Role, Span]] = []
    for comp in _iter_all(component):
        kind = comp.KIND
        if kind in _FS_ROLE:
            path = comp.files[0] if comp.files else None
            units.append((comp.name, _FS_ROLE[kind], Span(str(path) if path is not None else "", 0, 0)))
        elif kind is ScopeKind.CLASS and comp.name not in _UNNAMED:
            units.append((comp.name, Role.CLASS, comp.id.spans[0]))
            units.extend((p, Role.PROPERTY, comp.id.spans[0]) for p in comp.properties())
        elif kind is ScopeKind.CALLABLE:
            grammar = comp._grammar
            if comp.name not in _UNNAMED and not grammar.is_special_method(comp.name):
                units.append((comp.name, Role.CALLABLE, comp.id.spans[0]))
            receivers = grammar.implicit_receiver_names()
            units.extend((p, Role.PARAMETER, comp.id.spans[0])
                         for p in comp.parameters() if p not in receivers)
    return Lexicon(units)


def _node_holding_nodes(component: Any):
    """Yield the ``ast.Node`` of each node-holding component in the extent.
    Node-holding components (Module/Class/Callable) own a subtree; aggregates
    recurse to their node-holding descendants, so each file is reached once."""
    if component._node is not None:
        yield component._ast_node()
    else:
        for ch in component.children():
            yield from _node_holding_nodes(ch)


def _iter_all(component: Any):
    yield component
    for ch in component.children():
        yield from _iter_all(ch)
