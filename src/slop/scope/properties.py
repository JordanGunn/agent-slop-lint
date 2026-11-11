"""The properties a class declares: its field definitions, read from name binding.

A property is vocabulary chosen where it is declared, so it belongs in the declared-names
lexicon beside classes and callables. A grammar's locals query marks a class's fields
(``@local.definition.field``): declared fields (Java, C#, C++, TypeScript), struct fields (Go,
Rust, C, Julia), class-level names (Python), and members a method assigns through its instance
(``self.x = ...``, ``this.x = ...``, ``@x = ...``). An update (``self.x += 1``) declares nothing.
"""
from __future__ import annotations

from typing import Any

from ..ast.binding import SymbolKind


def class_properties(cls: Any) -> tuple[str, ...]:
    """Property names of the class component ``cls`` in first-seen order, without duplicates
    or special names, and without the fields of classes nested inside it."""
    node, grammar = cls._node, cls._grammar
    nested = [(n.start_byte, n.end_byte) for n in _descendants(node) if n.type in grammar.classes()]
    names: dict[str, None] = {}
    for start, binding in sorted(cls.bindings().items()):
        if (binding.kind is SymbolKind.FIELD and binding.defines and node.start_byte <= start < node.end_byte
                and not any(a <= start < b for a, b in nested) and not grammar.is_special_method(binding.text)):
            names.setdefault(binding.text, None)
    return tuple(names)


def _descendants(node: Any):
    stack = list(node.children)
    while stack:
        current = stack.pop()
        yield current
        stack.extend(current.children)
