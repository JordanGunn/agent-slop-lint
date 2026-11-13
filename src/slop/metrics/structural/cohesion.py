"""Class cohesion: LCOM4 (Hitz and Montazeri, 1995).

Build a graph whose nodes are a class's member names and whose edges join a method to every
member it reaches through its own instance (``self.x``, ``this.x``). A method is itself a
member, so a method that calls ``self.g()`` is joined to ``g``, and two methods that touch
the same attribute are joined through it. LCOM4 is the number of connected components that
contain a method: 1 is a class whose methods all lean on one another, more than 1 is a
class that is several classes sharing a name, and the groups say which methods go together.

Static and class methods have no instance, and constructors touch every member they
initialise (joining everything), so both are left out. A method that reaches no instance
member and is reached by no method (an abstract method, a property returning a constant) is
*detached*: it has no state to share or to split, so it is reported apart and is not a group. Without that,
every interface and every enum-like class would read as a pile of unrelated classes. A getter
or setter (``CallableKind.ACCESSOR``, ``slop.ast.accessor``) touches one field by definition, so
it is listed apart too; counting it would split every value class into one group per field
(Sharma, "Revisiting LCOM", 2017). A method counts the instance
accesses inside its nested callables too: a closure captures ``self``. A nested JavaScript
``function`` rebinds ``this``, which this measure does not model.

A method reaches a member two ways: through its instance (``self.x``, ``this.x``, ``s.x``,
the grammar's ``member_access``), or by a bare name that binds to a field or method of its own
class (Java, C#, C++ ``x`` for ``this.x``, Ruby ``helper`` and ``@x``; ``slop.ast.binding``).
Only the class's own members count: an inherited member is not visible without resolving the
base class's file, and both PMD and the CK tool exclude them. Java, C# and C++ name a
constructor after its class, so a method named like its class is a constructor too. A
language without instance members (C, Julia) has no answer, and the measure returns ``None``.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import replace
from typing import Any

from ...ast import NodeKind
from ...ast.binding import SymbolKind
from ...identity import CallableKind
from .records import Cohesion


_ANONYMOUS = "<anonymous>"


def cohesion(methods: Sequence[Any], grammar: Any) -> Cohesion | None:
    """The groups of methods joined through shared instance members, in declaration order
    of each group's first method, and the detached methods; ``None`` when ``grammar``
    cannot read instance access.

    ``methods`` are the class's method components (``name``, ``_node``, ``_content``,
    ``_ast_node()``)."""
    spellings = grammar.member_access()
    if not spellings:
        return None
    parent: dict[str, str] = {}
    measured: list[str] = []
    accessors: list[str] = []
    for method in methods:
        name = _method_name(method)
        if method.kind is CallableKind.CONSTRUCTOR:
            continue
        receiver = grammar.instance_receiver(method._node, method._content)
        if receiver is None:
            continue
        if method.kind is CallableKind.ACCESSOR:
            accessors.append(name)
            continue
        if name not in measured:
            measured.append(name)
        _find(parent, name)
        for member in _accessed_members(method, spellings, receiver):
            parent[_find(parent, member)] = _find(parent, name)
    return replace(_split(measured, parent), accessors=tuple(accessors))


def _method_name(method: Any) -> str:
    """The method's name; unnamed callables (a JS/TS class field holding an arrow function)
    are distinct methods, so each gets its line, as one shared name would join unrelated ones."""
    if method.name == _ANONYMOUS:
        return f"{_ANONYMOUS}:{method.line}"
    return method.name


def _find(parent: dict[str, str], name: str) -> str:
    """The representative of ``name``'s component, compressing the path walked."""
    parent.setdefault(name, name)
    while parent[name] != name:
        parent[name] = parent[parent[name]]
        name = parent[name]
    return name


def _accessed_members(method: Any, spellings: Any, receiver: str) -> Iterator[str]:
    """The member names ``method`` reaches through ``receiver`` or by a bare name bound to its
    own class's field or method, nested callables included."""
    by_type = {s.node_type: s for s in spellings}
    for node in method._ast_node().walk(prune=frozenset({NodeKind.CLASS})):
        access = by_type.get(node.type)
        if access is None:
            continue
        target, member = node.field(access.receiver_field), node.field(access.member_field)
        if target is not None and member is not None and target.text == receiver:
            yield member.text
    yield from _bound_members(method)


def _bound_members(method: Any) -> Iterator[str]:
    """Bare names in ``method`` that bind to a field or method of the class that owns it."""
    owner = method.owner._node
    start, end = method._node.start_byte, method._node.end_byte
    for at, binding in method.bindings().items():
        if not (start <= at < end) or binding.kind not in (SymbolKind.FIELD, SymbolKind.METHOD):
            continue
        if binding.definition is None or owner.start_byte <= binding.definition < owner.end_byte:
            yield binding.text


def _split(measured: list[str], parent: dict[str, str]) -> Cohesion:
    """Groups the measured methods by component; a method alone in its component reaches no
    instance state, so it is detached."""
    size: dict[str, int] = {}
    for name in list(parent):
        root = _find(parent, name)
        size[root] = size.get(root, 0) + 1
    attached = {name for name in measured if size[_find(parent, name)] > 1}
    groups: dict[str, list[str]] = {}
    for name in measured:
        if name in attached:
            groups.setdefault(_find(parent, name), []).append(name)
    return Cohesion(
        groups=tuple(tuple(g) for g in groups.values()),
        detached=tuple(n for n in measured if n not in attached),
    )
