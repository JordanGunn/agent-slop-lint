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
    return _cognitive_walk(
        node.body(), decision_nodes, grammar.nesting_nodes(),
        grammar.compensating_decisions(), grammar.boolean_op_node(),
        grammar.boolean_op_operators(), grammar.callable(),
    )


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
    then_np = 1
    consequence = node.field("consequence")
    if consequence is not None and consequence.type in vocab.block_types:
        then_np = _npath_of_block(consequence, vocab)
    else:
        for child in node.children():
            if child.type in vocab.block_types:
                then_np = _npath_of_block(child, vocab)
                break
    alt_nps: list[int] = []
    has_terminal = False
    for child in node.children():
        if child.type in vocab.elif_nodes:
            elif_body_np = 1
            for ec in child.children():
                if ec.type in vocab.block_types:
                    elif_body_np = _npath_of_block(ec, vocab)
            alt_nps.append(elif_body_np)
        elif child.type in vocab.else_nodes:
            has_terminal = True
            else_added = False
            for ec in child.children():
                if ec.type in vocab.block_types:
                    alt_nps.append(_npath_of_block(ec, vocab)); else_added = True
                elif ec.type in vocab.if_nodes:
                    alt_nps.append(_npath_of_if(ec, vocab)); else_added = True
            if not else_added and not vocab.body_field:
                alt_nps.append(1)
    if vocab.bare_else_keyword and not has_terminal:
        children = list(node.children())
        for i, child in enumerate(children):
            if child.type == vocab.bare_else_keyword and i + 1 < len(children):
                nxt = children[i + 1]
                has_terminal = True
                if nxt.type in vocab.block_types:
                    alt_nps.append(_npath_of_block(nxt, vocab))
                elif nxt.type in vocab.if_nodes:
                    alt_nps.append(_npath_of_if(nxt, vocab))
    if not has_terminal:
        return then_np + sum(alt_nps) + 1
    return then_np + sum(alt_nps)


# ---- cognitive -----------------------------------------------------------

def _cognitive_walk(
    root: Any, decision_nodes: frozenset[str], nesting_nodes: frozenset[str],
    compensating: frozenset[str], bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None, nested_callables: frozenset[str],
) -> int:
    cog = 0
    stack: list[tuple[Any, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        ctype = node.type
        if ctype in nested_callables and node is not root:
            continue
        if ctype in decision_nodes:
            cog += (1 + max(0, depth - 1)) if ctype in compensating else (1 + depth)
        if bool_op_node is not None and ctype == bool_op_node:
            op_text = _bool_op_text(node)
            counts = (bool_op_operators is None) or (op_text in bool_op_operators)
            if counts:
                parent = node.parent
                in_continuing = False
                if parent is not None and parent.type == bool_op_node:
                    parent_op = _bool_op_text(parent)
                    if (bool_op_operators is None or parent_op in bool_op_operators) and parent_op == op_text:
                        in_continuing = True
                if not in_continuing:
                    cog += 1
        new_depth = depth + 1 if ctype in nesting_nodes else depth
        for child in reversed(node.children()):
            stack.append((child, new_depth))
    return cog
