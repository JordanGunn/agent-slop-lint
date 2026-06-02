"""AST + Node — slop's only proxy over tree-sitter.

Nothing outside ``ast/grammar/`` and this module touches a raw tree-sitter node.
``AST`` parses one file and owns the ``tree_sitter.Tree`` for its lifetime (so
node references stay valid); ``Node`` is a pythonic wrapper over one raw node,
self-sufficient given ``(raw, content, path, grammar)``.

The boundary this enforces: the AST owns *navigation* (DFS, child/field access,
text decode, byte-span, type filtering, queries, body unwrap, render). It does
NOT own metric *math* — structure-directed algorithms (NPath, cognitive scoring)
re-express against this API and stay as compute elsewhere.

Identity is the span, never ``id(node)`` — tree-sitter node identity is not
stable across accesses.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from ..span import Span
from .nodes import NodeKind
from .parse import parse_file


class Node:
    """A pythonic proxy over one tree-sitter node — the only way the rest of
    slop reads syntax. The grammar turns a raw ``.type`` into a neutral ``.kind``.
    """

    __slots__ = ("_raw", "_content", "_path", "_grammar")

    def __init__(self, raw: Any, content: bytes, path: Path, grammar: Any) -> None:
        self._raw = raw
        self._content = content
        self._path = path
        self._grammar = grammar

    def _wrap(self, raw: Any) -> "Node":
        return Node(raw, self._content, self._path, self._grammar)

    # ---- identity (keyed on span, never id(node)) --------------------
    @property
    def span(self) -> Span:
        return Span(str(self._path), self._raw.start_byte, self._raw.end_byte)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Node) and other.span == self.span

    def __hash__(self) -> int:
        return hash(self.span)

    # ---- raw + neutral type ------------------------------------------
    @property
    def type(self) -> str:
        """Raw tree-sitter node type — the escape hatch for the long tail."""
        return self._raw.type

    @property
    def raw(self) -> Any:
        """The underlying tree-sitter node. The one sanctioned escape hatch:
        handing a node to the grammar translation layer (whose ``extract_*``
        methods take raw nodes and legitimately live inside ast/). Code above
        ast/ must not *navigate* a raw node — pass the opaque handle, no more."""
        return self._raw

    @property
    def named(self) -> bool:
        return self._raw.is_named

    @property
    def child_count(self) -> int:
        return self._raw.child_count

    @property
    def line(self) -> int:
        """1-based start line of this node."""
        return self._raw.start_point[0] + 1

    @property
    def kind(self) -> NodeKind:
        """Neutral category, derived from the grammar's own vocabulary."""
        return _classify(self._raw.type, self._grammar)

    @property
    def text(self) -> str:
        return self._content[self._raw.start_byte:self._raw.end_byte].decode("utf-8", errors="replace")

    # ---- navigation --------------------------------------------------
    @property
    def parent(self) -> "Node | None":
        p = self._raw.parent
        return self._wrap(p) if p is not None else None

    def children(self) -> tuple["Node", ...]:
        return tuple(self._wrap(c) for c in self._raw.children)

    def field(self, name: str) -> "Node | None":
        c = self._raw.child_by_field_name(name)
        return self._wrap(c) if c is not None else None

    def body(self) -> "Node":
        """Unwrap definition wrappers, then descend to the ``body`` field.

        Replaces the hand-rolled ``resolve_body``: ``definition_unwrap_types``
        names wrapper nodes (e.g. C++ ``template_declaration``) the walker steps
        through before reading the body. Falls back to the unwrapped node when
        there is no ``body`` field.
        """
        current = self.unwrap()
        b = current._raw.child_by_field_name("body")
        return current._wrap(b) if b is not None else current

    def unwrap(self) -> "Node":
        """Step through definition-wrapper nodes (e.g. C++ ``template_declaration``)
        to the inner definition, without descending to its body. NPath unwraps
        then does its own body-field handling."""
        unwrap = self._grammar.definition_unwrap_types()
        raw = self._raw
        for _ in range(4):
            if raw.type not in unwrap:
                break
            nxt = None
            for child in raw.children:
                if child.type != raw.type and child.type not in ("(", ")", "<", ">", ","):
                    nxt = child
                    break
            if nxt is None:
                break
            raw = nxt
        return self._wrap(raw)

    def walk(self, prune: "frozenset[NodeKind]" = frozenset()) -> Iterator["Node"]:
        """Pre-order DFS from this node. Descent stops at (but still yields) nodes
        whose ``kind`` is in ``prune`` — the "do not cross nested callables" need,
        expressed neutrally. The starting node is always descended.
        """
        yield self
        stack = list(reversed(self._raw.children))
        while stack:
            raw = stack.pop()
            node = self._wrap(raw)
            yield node
            if prune and node.kind in prune:
                continue
            stack.extend(reversed(raw.children))

    def identifiers(self) -> Iterator[tuple[str, Span]]:
        """Yield ``(text, span)`` for every identifier token in this subtree.

        Identifier-hood is the grammar's own classification
        (``NodeKind.IDENTIFIER``, i.e. ``grammar.identifiers()``), not a
        name-shape heuristic: that counts only *leaf* identifiers, so container
        types like C++ ``scoped_identifier`` ("a::b") neither double-count their
        children nor leak punctuated pseudo-tokens. This is the AST's whole
        contribution to the lexicon — words *as written*, with location; deciding
        what counts as vocabulary (splitting ``fooBar``, stripping noise) is the
        lexicon's job, above this boundary.
        """
        for node in self.walk():
            if node.kind is NodeKind.IDENTIFIER:
                yield node.text, node.span

    def query(self, pattern: str, capture: str | None = None) -> tuple["Node", ...]:
        """Run a tree-sitter query rooted at this node. With ``capture``, return
        only nodes bound to that capture name (e.g. ``"module"`` for ``@module``);
        otherwise every captured node, flattened. Wraps the modern
        ``Query``/``QueryCursor`` API with the pre-0.22 fallback, matching the
        loader shim in ``parse.py``."""
        ts_lang = self._grammar.ts_language()
        if ts_lang is None:
            return ()
        import tree_sitter

        out: list[Node] = []
        query_cls = getattr(tree_sitter, "Query", None)
        cursor_cls = getattr(tree_sitter, "QueryCursor", None)
        if query_cls is not None and cursor_cls is not None:
            cursor = cursor_cls(query_cls(ts_lang, pattern))
            for _idx, captures in cursor.matches(self._raw):
                out.extend(self._wrap(n) for n in _captured_nodes(captures, capture))
        else:
            query = ts_lang.query(pattern)
            for match in query.matches(self._raw):
                if isinstance(match, tuple) and len(match) == 2:
                    out.extend(self._wrap(n) for n in _captured_nodes(match[1], capture))
        return tuple(out)

    # ---- inspection / serialization ----------------------------------
    def render(self, indent: int = 0) -> str:
        """ASCII tree from this node down — the standalone inspector / visualizer."""
        pad = "  " * indent
        label = self._raw.type if self._raw.is_named else f'"{self._raw.type}"'
        lines = [f"{pad}{label} [{self._raw.start_byte}:{self._raw.end_byte}]"]
        for child in self._raw.children:
            lines.append(self._wrap(child).render(indent + 1))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialisable tree (json/yaml dump) from this node down."""
        return {
            "type": self._raw.type,
            "kind": self.kind.value,
            "named": self._raw.is_named,
            "span": [self._raw.start_byte, self._raw.end_byte],
            "children": [self._wrap(c).to_dict() for c in self._raw.children],
        }


class AST:
    """One parsed source file. Owns the ``tree_sitter.Tree`` (keeps it alive so
    held node references stay valid), the source bytes, the path, and the grammar.

    Per file by design: a component whose extent spans several files (a Go module,
    a reopened class) is the *component layer's* composition over multiple ``AST``s.
    ``ast/`` does not model forests.
    """

    __slots__ = ("_tree", "_content", "_path", "_grammar")

    def __init__(self, tree: Any, content: bytes, path: Path, grammar: Any) -> None:
        self._tree = tree
        self._content = content
        self._path = Path(path)
        self._grammar = grammar

    @classmethod
    def parse(cls, path: Path, grammar: Any) -> "AST | None":
        """Parse ``path`` with ``grammar``; None on read/parse failure."""
        result = parse_file(Path(path), grammar.id)
        if result is None:
            return None
        tree, content = result
        return cls(tree, content, Path(path), grammar)

    @property
    def root(self) -> Node:
        return Node(self._tree.root_node, self._content, self._path, self._grammar)

    def node(self, raw: Any) -> Node:
        """Wrap a raw node already drawn from this tree (carving holds raw nodes
        during the migration; this re-enters them into the proxy)."""
        return Node(raw, self._content, self._path, self._grammar)

    def at(self, span: Span) -> "Node | None":
        """Smallest node whose byte range covers ``span`` (was ``_descend_to_span``)."""
        raw = self._tree.root_node
        if not (raw.start_byte <= span.start_byte and raw.end_byte >= span.end_byte):
            return None
        descended = True
        while descended:
            descended = False
            for child in raw.children:
                if child.start_byte <= span.start_byte and child.end_byte >= span.end_byte:
                    raw = child
                    descended = True
                    break
        return Node(raw, self._content, self._path, self._grammar)

    def render(self) -> str:
        return self.root.render()


# ---- raw type -> neutral kind (grammar-driven; cached per grammar) -------

_VOCAB_CACHE: dict = {}


def _grammar_vocab(grammar: Any) -> dict:
    """The grammar's category sets, computed once. The grammar already
    classifies raw types (``callable()``/``decision_nodes()``/...); ``kind`` only
    reorders those into the neutral vocabulary — no separate table."""
    cached = _VOCAB_CACHE.get(grammar)
    if cached is not None:
        return cached
    bon = grammar.boolean_op_node()
    v = {
        "callable": grammar.callable(),
        "classes": grammar.classes() if hasattr(grammar, "classes") else frozenset(),
        "loop": grammar.loop_nodes(),
        "switch": grammar.switch_nodes(),
        "case": grammar.case_nodes(),
        "try": grammar.try_nodes(),
        "catch": grammar.catch_nodes(),
        "branch": grammar.if_nodes() | grammar.elif_nodes() | grammar.decision_nodes(),
        "bool_op": frozenset({bon}) if bon else frozenset(),
        "call": grammar.call_node_types(),
        "identifier": grammar.identifiers(),
        "literal": grammar.numeric_literal_nodes(),
    }
    _VOCAB_CACHE[grammar] = v
    return v


def _classify(raw_type: str, grammar: Any) -> NodeKind:
    v = _grammar_vocab(grammar)
    # Specific (loop/switch/...) before generic BRANCH: the formers are subsets
    # of decision_nodes, so order disambiguates the overlap.
    if raw_type in v["callable"]:
        return NodeKind.CALLABLE
    if raw_type in v["classes"]:
        return NodeKind.CLASS
    if raw_type in v["loop"]:
        return NodeKind.LOOP
    if raw_type in v["switch"]:
        return NodeKind.SWITCH
    if raw_type in v["case"]:
        return NodeKind.CASE
    if raw_type in v["try"]:
        return NodeKind.TRY
    if raw_type in v["catch"]:
        return NodeKind.CATCH
    if raw_type in v["branch"]:
        return NodeKind.BRANCH
    if raw_type in v["bool_op"]:
        return NodeKind.BOOLEAN_OP
    if raw_type in v["call"]:
        return NodeKind.CALL
    if raw_type in v["literal"]:
        return NodeKind.LITERAL
    if raw_type in v["identifier"]:
        return NodeKind.IDENTIFIER
    # IMPORT / PARAMETER are query/extractor-derived, not single-type sets; they
    # map through OTHER until a consumer needs them.
    return NodeKind.OTHER


def _captured_nodes(captures: Any, name: str | None = None) -> Iterator[Any]:
    """Yield raw nodes from a tree-sitter match's captures, across both the
    dict shape (modern) and the (name, node) pairs shape (legacy). With ``name``,
    yield only nodes bound to that capture name."""
    if isinstance(captures, dict):
        if name is not None:
            yield from captures.get(name, [])
        else:
            for nodes in captures.values():
                yield from nodes
        return
    for cname, node in captures:
        if name is None or cname == name:
            yield node
