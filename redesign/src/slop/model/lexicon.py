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

from ..component.identity import ComponentKind
from ..lexicon import Lexicon, Role
from ..span import Span

#: Filesystem-derived component names carry the grammatical-degradation signal
#: (module/package names come from the directory tree, not an AST node).
_FS_ROLE = {
    ComponentKind.REALM: Role.REALM,
    ComponentKind.PACKAGE: Role.PACKAGE,
    ComponentKind.MODULE: Role.MODULE,
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
