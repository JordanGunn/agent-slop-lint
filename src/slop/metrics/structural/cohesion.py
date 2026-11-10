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
every interface and every enum-like class would read as a pile of unrelated classes. A method counts the instance
accesses inside its nested callables too: a closure captures ``self``. A nested JavaScript
``function`` rebinds ``this``, which this measure does not model.

A grammar that cannot say how it spells instance member access (Java, C#, C++ allow a bare
``x`` for ``this.x``) has no answer, and the measure returns ``None`` rather than a count
that silently misses those accesses.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ...ast import NodeKind
from .records import Cohesion


def cohesion(methods: Sequence[Any], grammar: Any) -> Cohesion | None:
    """The groups of methods joined through shared instance members, in declaration order
    of each group's first method, and the detached methods; ``None`` when ``grammar``
    cannot read instance access.

    ``methods`` are the class's method components (``name``, ``_node``, ``_content``,
    ``_ast_node()``)."""
    access = grammar.member_access()
    if access is None:
        return None
    constructors = grammar.constructor_names()
    parent: dict[str, str] = {}

    def find(name: str) -> str:
        parent.setdefault(name, name)
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    measured: list[str] = []
    for method in methods:
        name = method.name
        if name == "<anonymous>":
            # Unnamed callables (a JS/TS class field holding an arrow function) are distinct
            # methods; one shared name would join unrelated ones.
            name = f"<anonymous>:{method.line}"
        if name in constructors:
            continue
        receiver = grammar.instance_receiver(method._node, method._content)
        if receiver is None:
            continue
        if name not in measured:
            measured.append(name)
        find(name)
        for node in method._ast_node().walk(prune=frozenset({NodeKind.CLASS})):
            if node.type != access.node_type:
                continue
            target, member = node.field(access.receiver_field), node.field(access.member_field)
            if target is not None and member is not None and target.text == receiver:
                parent[find(member.text)] = find(name)

    size: dict[str, int] = {}
    for name in list(parent):
        size[find(name)] = size.get(find(name), 0) + 1
    # Attached = shares a component with anything else: a member it touches, or a method
    # that touches it. Alone in its component it reaches no instance state.
    attached = {name for name in measured if size[find(name)] > 1}
    groups: dict[str, list[str]] = {}
    for name in measured:
        if name in attached:
            groups.setdefault(find(name), []).append(name)
    return Cohesion(
        groups=tuple(tuple(g) for g in groups.values()),
        detached=tuple(n for n in measured if n not in attached),
    )
