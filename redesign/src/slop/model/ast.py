"""Concrete AST projection — parsed syntax over a component's extent.

One ``AST`` type bound to an extent (the interface's contract), holding the
tree-sitter roots the component spans: one node for a Callable/Class, a file
root for a Module, a forest for an aggregate. Metrics walk it; ``slice`` narrows
to a sub-extent reusing the same parse (no re-parse).
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..component.identity import Extent, Span


@dataclass(frozen=True)
class Root:
    """One tree-sitter root this AST spans, with its file's content + path."""

    node: Any
    content: bytes
    path: Path


class AST:
    """Implements ``slop.component.projection.AST``. A forest of roots; for a
    single-node component (Callable/Class) it holds one root."""

    def __init__(self, roots: tuple[Root, ...]) -> None:
        self._roots = roots

    @property
    def roots(self) -> tuple[Root, ...]:
        return self._roots

    def walk(self) -> Iterator[tuple[Any, bytes, Path]]:
        """DFS every node across all roots, yielding (node, content, path)."""
        for root in self._roots:
            stack = [root.node]
            while stack:
                n = stack.pop()
                yield n, root.content, root.path
                stack.extend(n.children)

    def slice(self, extent: Extent) -> "AST":
        """Narrow to roots overlapping ``extent``'s spans (reuses the parse)."""
        by_path: dict[str, list[Span]] = {}
        for span in extent.spans:
            by_path.setdefault(span.path, []).append(span)
        kept: list[Root] = []
        for root in self._roots:
            spans = by_path.get(str(root.path))
            if not spans:
                continue
            for sp in spans:
                sub = _descend_to_span(root.node, sp)
                if sub is not None:
                    kept.append(Root(node=sub, content=root.content, path=root.path))
        return AST(tuple(kept))


def _descend_to_span(node: Any, span: Span) -> Any | None:
    """Smallest node fully covering the span, or the span's exact node."""
    if node.start_byte == span.start_byte and node.end_byte == span.end_byte:
        return node
    if node.start_byte <= span.start_byte and node.end_byte >= span.end_byte:
        for child in node.children:
            found = _descend_to_span(child, span)
            if found is not None:
                return found
        return node
    return None
