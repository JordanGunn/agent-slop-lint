"""Per-callable complexity walkers — cyclomatic, cognitive, NPath.

Encodes the McCabe 1976 / Campbell 2018 / Nejmeh 1988 definitions — real
algorithms, not navigation. All three now run on the ``slop.ast`` ``Node``
proxy: ``node.body()`` / ``node.unwrap()`` replace the hand-rolled body
resolution, and child/field access goes through ``Node``. The decision/boolean
*vocabulary* (which raw types count) stays as grammar data — that is the
language fact, not traversal. Each walker is body-local: it does not descend
into nested callables, so container aggregates sum each leaf exactly once.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...ast import NodeKind


# ---- public entry points -------------------------------------------------

def cyclomatic(node: Any, grammar: Any) -> int:
    """McCabe (1976): decisions + short-circuit booleans + 1.

    ``node.body()`` resolves the body; ``Node.walk(prune={CALLABLE})`` is the
    body-local DFS that does not cross nested callables.
    """
    decision_nodes = grammar.decision_nodes()
    if not decision_nodes:
        return 1
    bool_op_node = grammar.boolean_op_node()
    bool_ops = grammar.boolean_op_operators()
    count = 0
    for n in node.body().walk(prune=frozenset({NodeKind.CALLABLE})):
        ntype = n.type
        if ntype in decision_nodes:
            count += 1
        if bool_op_node is not None and ntype == bool_op_node:
            if bool_ops is None or _bool_op_text(n) in bool_ops:
                count += 1
    return count + 1


def cognitive(node: Any, grammar: Any) -> int:
    """Campbell (2018): nesting-penalised, compensated, chain-collapsed."""
    decision_nodes = grammar.decision_nodes()
    if not decision_nodes:
        return 0
    vocab = _CognitiveVocab(
        decision_nodes, grammar.nesting_nodes(), grammar.compensating_decisions(),
        grammar.boolean_op_node(), grammar.boolean_op_operators(), grammar.callable(),
    )
    return _cognitive_walk(node.body(), vocab)


def combinatorial(node: Any, grammar: Any) -> int:
    """Nejmeh (1988) NPath — multiplicative acyclic path count."""
    vocab = _NPathVocab.for_grammar(grammar)
    return max(1, _npath_walk(node.unwrap(), vocab))


# ---- shared helper -------------------------------------------------------

def _bool_op_text(node: Any) -> str:
    """The operator text of a boolean-op node, on the Node proxy."""
    op = node.field("operator")
    if op is not None:
        return op.text
    for child in node.children():
        ctype = child.type
        if ctype == "operator":
            return child.text
        if ctype in ("and", "or", "not"):
            return ctype
        if not child.named:
            text = child.text
            if text in ("&&", "||", "??", "and", "or"):
                return text
    return ""


# ---- combinatorial (NPath) -----------------------------------------------

@dataclass(frozen=True)
class _NPathVocab:
    if_nodes: frozenset[str]
    elif_nodes: frozenset[str]
    else_nodes: frozenset[str]
    loop_nodes: frozenset[str]
    switch_nodes: frozenset[str]
    case_nodes: frozenset[str]
    try_nodes: frozenset[str]
    catch_nodes: frozenset[str]
    body_field: str
    block_types: frozenset[str]
    switch_body_types: frozenset[str]
    body_skip_types: frozenset[str]
    bare_else_keyword: str | None
    nested_callables: frozenset[str]

    @classmethod
    def for_grammar(cls, g: Any) -> "_NPathVocab":
        return cls(
            if_nodes=g.if_nodes(), elif_nodes=g.elif_nodes(), else_nodes=g.else_nodes(),
            loop_nodes=g.loop_nodes(), switch_nodes=g.switch_nodes(), case_nodes=g.case_nodes(),
            try_nodes=g.try_nodes(), catch_nodes=g.catch_nodes(), body_field=g.body_field(),
            block_types=g.block_types(), switch_body_types=g.switch_body_types(),
            body_skip_types=g.body_skip_types(), bare_else_keyword=g.bare_else_keyword(),
            nested_callables=g.callable(),
        )


def _npath_walk(callable_node: Any, vocab: _NPathVocab) -> int:
    if vocab.body_field:
        body = callable_node.field(vocab.body_field)
        if body is None:
            return 1
        return _npath_of_block(body, vocab)
    return _npath_of_flat_body(callable_node, vocab)


def _npath_of_block(node: Any, vocab: _NPathVocab) -> int:
    if node is None:
        return 1
    if node.type in vocab.block_types:
        result = 1
        for child in node.children():
            result *= _npath_of_node(child, vocab)
        return result
    return _npath_of_node(node, vocab)


def _npath_of_flat_body(node: Any, vocab: _NPathVocab) -> int:
    result = 1
    for child in node.children():
        if child.type in vocab.body_skip_types:
            continue
        cn = _npath_of_node(child, vocab)
        if cn > 1:
            result *= cn
    return result


def _npath_of_node(node: Any, vocab: _NPathVocab) -> int:
    ntype = node.type
    if ntype in vocab.if_nodes or ntype in vocab.elif_nodes:
        return _npath_of_if(node, vocab)
    if ntype in vocab.loop_nodes:
        if vocab.body_field:
            body = node.field(vocab.body_field)
            return _npath_of_block(body, vocab) + 1
        return _npath_of_flat_body(node, vocab) + 1
    if ntype in vocab.switch_nodes:
        return _npath_of_switch(node, vocab)
    if ntype in vocab.try_nodes:
        return _npath_of_try(node, vocab)
    if ntype in vocab.nested_callables:
        return 1
    result = 1
    for child in node.children():
        cn = _npath_of_node(child, vocab)
        if cn > 1:
            result *= cn
    return result


def _npath_of_switch(node: Any, vocab: _NPathVocab) -> int:
    def iter_cases(parent: Any):
        for child in parent.children():
            if child.type in vocab.case_nodes:
                yield child
            elif child.type in vocab.switch_body_types:
                yield from iter_cases(child)
    total = 0
    for case_child in iter_cases(node):
        case_np = 1
        for cc in case_child.children():
            if cc.type in vocab.block_types:
                case_np = _npath_of_block(cc, vocab)
        total += case_np
    return max(total, 1)


def _npath_of_try(node: Any, vocab: _NPathVocab) -> int:
    try_body_np = 1
    handler_sum = 0
    for child in node.children():
        if child.type in vocab.block_types:
            try_body_np = _npath_of_block(child, vocab)
        elif child.type in vocab.catch_nodes:
            if vocab.body_field:
                catch_body = child.field(vocab.body_field)
                handler_sum += _npath_of_block(catch_body, vocab) if catch_body is not None else 1
            else:
                handler_sum += _npath_of_flat_body(child, vocab)
    return try_body_np if handler_sum == 0 else try_body_np + handler_sum


def _npath_of_if(node: Any, vocab: _NPathVocab) -> int:
    children = list(node.children())
    alternatives: list[int] = []
    has_terminal = False
    for child in children:
        if child.type in vocab.elif_nodes:
            alternatives.append(_npath_of_elif(child, vocab))
        elif child.type in vocab.else_nodes:
            has_terminal = True
            alternatives.extend(_npath_of_else(child, vocab))
    if vocab.bare_else_keyword and not has_terminal:
        bare = _npath_of_bare_else(children, vocab)
        if bare is not None:
            has_terminal = True
            alternatives.extend(bare)
    implicit_else = 0 if has_terminal else 1
    return _npath_of_then(node, vocab) + sum(alternatives) + implicit_else


def _npath_of_then(node: Any, vocab: _NPathVocab) -> int:
    consequence = node.field("consequence")
    if consequence is not None and consequence.type in vocab.block_types:
        return _npath_of_block(consequence, vocab)
    for child in node.children():
        if child.type in vocab.block_types:
            return _npath_of_block(child, vocab)
    return 1


def _npath_of_elif(node: Any, vocab: _NPathVocab) -> int:
    result = 1
    for child in node.children():
        if child.type in vocab.block_types:
            result = _npath_of_block(child, vocab)
    return result


def _npath_of_else(node: Any, vocab: _NPathVocab) -> list[int]:
    """Path counts of an else clause: its blocks and chained ifs, else one empty path."""
    paths = [
        _npath_of_branch(child, vocab)
        for child in node.children()
        if child.type in vocab.block_types or child.type in vocab.if_nodes
    ]
    if not paths and not vocab.body_field:
        paths.append(1)
    return paths


def _npath_of_bare_else(children: list[Any], vocab: _NPathVocab) -> list[int] | None:
    """Path counts after bare ``else`` keywords among siblings; None when there is none."""
    found = False
    paths: list[int] = []
    for child, following in zip(children, children[1:]):
        if child.type != vocab.bare_else_keyword:
            continue
        found = True
        if following.type in vocab.block_types or following.type in vocab.if_nodes:
            paths.append(_npath_of_branch(following, vocab))
    return paths if found else None


def _npath_of_branch(node: Any, vocab: _NPathVocab) -> int:
    if node.type in vocab.block_types:
        return _npath_of_block(node, vocab)
    return _npath_of_if(node, vocab)


# ---- cognitive -----------------------------------------------------------

@dataclass(frozen=True)
class _CognitiveVocab:
    decision_nodes: frozenset[str]
    nesting_nodes: frozenset[str]
    compensating: frozenset[str]
    bool_op_node: str | None
    bool_op_operators: frozenset[str] | None
    nested_callables: frozenset[str]

    def decision_cost(self, ctype: str, depth: int) -> int:
        if ctype not in self.decision_nodes:
            return 0
        if ctype in self.compensating:
            return 1 + max(0, depth - 1)
        return 1 + depth

    def counts_operator(self, op_text: str) -> bool:
        return self.bool_op_operators is None or op_text in self.bool_op_operators

    def bool_op_cost(self, node: Any) -> int:
        """One for each boolean operator that starts a run; a repeated operator costs nothing."""
        if self.bool_op_node is None or node.type != self.bool_op_node:
            return 0
        op_text = _bool_op_text(node)
        if not self.counts_operator(op_text):
            return 0
        parent = node.parent
        if parent is not None and parent.type == self.bool_op_node and _bool_op_text(parent) == op_text:
            return 0
        return 1

    def node_cost(self, node: Any, depth: int) -> int:
        return self.decision_cost(node.type, depth) + self.bool_op_cost(node)


def _cognitive_walk(root: Any, vocab: _CognitiveVocab) -> int:
    cog = 0
    stack: list[tuple[Any, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node.type in vocab.nested_callables and node is not root:
            continue
        cog += vocab.node_cost(node, depth)
        child_depth = depth + 1 if node.type in vocab.nesting_nodes else depth
        stack.extend((child, child_depth) for child in reversed(node.children()))
    return cog
