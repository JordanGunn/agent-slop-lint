"""Per-callable complexity walkers — cyclomatic, cognitive, NPath.

Faithful port of the legacy ``structure/complexity.py`` (these encode the
McCabe 1976 / Campbell 2018 / Nejmeh 1988 definitions — real algorithm, not
structure). The only change is the parameter name (``lang`` → ``grammar``); the
metadata methods it reads are identical on the ported ``Grammar``. Each walker
is body-local: it does not descend into nested callables, so container
aggregates sum each leaf exactly once.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


# ---- public entry points -------------------------------------------------

def cyclomatic(node: Any, content: bytes, grammar: Any) -> int:
    """McCabe (1976): decisions + short-circuit booleans + 1."""
    decision_nodes = grammar.decision_nodes()
    if not decision_nodes:
        return 1
    walk_from = resolve_body(node, grammar.definition_unwrap_types())
    return _count_decisions(
        walk_from, decision_nodes, grammar.boolean_op_node(),
        grammar.boolean_op_operators(), grammar.callable(), content,
    ) + 1


def cognitive(node: Any, content: bytes, grammar: Any) -> int:
    """Campbell (2018): nesting-penalised, compensated, chain-collapsed."""
    decision_nodes = grammar.decision_nodes()
    if not decision_nodes:
        return 0
    walk_from = resolve_body(node, grammar.definition_unwrap_types())
    return _cognitive_walk(
        walk_from, decision_nodes, grammar.nesting_nodes(),
        grammar.compensating_decisions(), grammar.boolean_op_node(),
        grammar.boolean_op_operators(), grammar.callable(), content,
    )


def combinatorial(node: Any, grammar: Any) -> int:
    """Nejmeh (1988) NPath — multiplicative acyclic path count."""
    vocab = _NPathVocab.for_grammar(grammar)
    node = _unwrap_definition(node, vocab.definition_unwrap_types)
    return max(1, _npath_walk(node, vocab))


# ---- shared helpers ------------------------------------------------------

def _unwrap_definition(node: Any, unwrap: frozenset[str]) -> Any:
    current = node
    for _ in range(4):
        if current.type not in unwrap:
            break
        next_node = None
        for child in current.children:
            if child.type != current.type and child.type not in ("(", ")", "<", ">", ","):
                next_node = child
                break
        if next_node is None:
            break
        current = next_node
    return current


def resolve_body(node: Any, unwrap: frozenset[str]) -> Any:
    """Unwrap to the definition then descend to its ``body`` field."""
    current = _unwrap_definition(node, unwrap)
    body = current.child_by_field_name("body")
    return body if body is not None else current


def _bool_op_text(node: Any, content: bytes) -> str:
    op_node = node.child_by_field_name("operator")
    if op_node is not None:
        return content[op_node.start_byte:op_node.end_byte].decode("utf-8", errors="replace")
    for child in node.children:
        if child.type == "operator":
            return content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
        if child.type in ("and", "or", "not"):
            return child.type
        if not child.is_named:
            text = content[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
            if text in ("&&", "||", "??", "and", "or"):
                return text
    return ""


def _bool_op_matches(node: Any, operators: frozenset[str], content: bytes) -> bool:
    op_text = _bool_op_text(node, content)
    return op_text in operators if op_text else False


# ---- cyclomatic ----------------------------------------------------------

def _count_decisions(
    node: Any, decision_nodes: frozenset[str], bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None, nested_callables: frozenset[str], content: bytes,
) -> int:
    count = 0
    stack = [node]
    while stack:
        cur = stack.pop()
        ctype = cur.type
        if ctype in nested_callables and cur is not node:
            continue
        if ctype in decision_nodes:
            count += 1
        if bool_op_node is not None and ctype == bool_op_node:
            if bool_op_operators is None or _bool_op_matches(cur, bool_op_operators, content):
                count += 1
        stack.extend(reversed(cur.children))
    return count


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
    definition_unwrap_types: frozenset[str]

    @classmethod
    def for_grammar(cls, g: Any) -> "_NPathVocab":
        return cls(
            if_nodes=g.if_nodes(), elif_nodes=g.elif_nodes(), else_nodes=g.else_nodes(),
            loop_nodes=g.loop_nodes(), switch_nodes=g.switch_nodes(), case_nodes=g.case_nodes(),
            try_nodes=g.try_nodes(), catch_nodes=g.catch_nodes(), body_field=g.body_field(),
            block_types=g.block_types(), switch_body_types=g.switch_body_types(),
            body_skip_types=g.body_skip_types(), bare_else_keyword=g.bare_else_keyword(),
            nested_callables=g.callable(), definition_unwrap_types=g.definition_unwrap_types(),
        )


def _npath_walk(callable_node: Any, vocab: _NPathVocab) -> int:
    if vocab.body_field:
        body = callable_node.child_by_field_name(vocab.body_field)
        if body is None:
            return 1
        return _npath_of_block(body, vocab)
    return _npath_of_flat_body(callable_node, vocab)


def _npath_of_block(node: Any, vocab: _NPathVocab) -> int:
    if node is None:
        return 1
    if node.type in vocab.block_types:
        result = 1
        for child in node.children:
            result *= _npath_of_node(child, vocab)
        return result
    return _npath_of_node(node, vocab)


def _npath_of_flat_body(node: Any, vocab: _NPathVocab) -> int:
    result = 1
    for child in node.children:
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
            body = node.child_by_field_name(vocab.body_field)
            return _npath_of_block(body, vocab) + 1
        return _npath_of_flat_body(node, vocab) + 1
    if ntype in vocab.switch_nodes:
        return _npath_of_switch(node, vocab)
    if ntype in vocab.try_nodes:
        return _npath_of_try(node, vocab)
    if ntype in vocab.nested_callables:
        return 1
    result = 1
    for child in node.children:
        cn = _npath_of_node(child, vocab)
        if cn > 1:
            result *= cn
    return result


def _npath_of_switch(node: Any, vocab: _NPathVocab) -> int:
    def iter_cases(parent: Any) -> Iterable[Any]:
        for child in parent.children:
            if child.type in vocab.case_nodes:
                yield child
            elif child.type in vocab.switch_body_types:
                yield from iter_cases(child)
    total = 0
    for case_child in iter_cases(node):
        case_np = 1
        for cc in case_child.children:
            if cc.type in vocab.block_types:
                case_np = _npath_of_block(cc, vocab)
        total += case_np
    return max(total, 1)


def _npath_of_try(node: Any, vocab: _NPathVocab) -> int:
    try_body_np = 1
    handler_sum = 0
    for child in node.children:
        if child.type in vocab.block_types:
            try_body_np = _npath_of_block(child, vocab)
        elif child.type in vocab.catch_nodes:
            if vocab.body_field:
                catch_body = child.child_by_field_name(vocab.body_field)
                handler_sum += _npath_of_block(catch_body, vocab) if catch_body is not None else 1
            else:
                handler_sum += _npath_of_flat_body(child, vocab)
    return try_body_np if handler_sum == 0 else try_body_np + handler_sum


def _npath_of_if(node: Any, vocab: _NPathVocab) -> int:
    then_np = 1
    consequence = node.child_by_field_name("consequence")
    if consequence is not None and consequence.type in vocab.block_types:
        then_np = _npath_of_block(consequence, vocab)
    else:
        for child in node.children:
            if child.type in vocab.block_types:
                then_np = _npath_of_block(child, vocab)
                break
    alt_nps: list[int] = []
    has_terminal = False
    for child in node.children:
        if child.type in vocab.elif_nodes:
            elif_body_np = 1
            for ec in child.children:
                if ec.type in vocab.block_types:
                    elif_body_np = _npath_of_block(ec, vocab)
            alt_nps.append(elif_body_np)
        elif child.type in vocab.else_nodes:
            has_terminal = True
            else_added = False
            for ec in child.children:
                if ec.type in vocab.block_types:
                    alt_nps.append(_npath_of_block(ec, vocab)); else_added = True
                elif ec.type in vocab.if_nodes:
                    alt_nps.append(_npath_of_if(ec, vocab)); else_added = True
            if not else_added and not vocab.body_field:
                alt_nps.append(1)
    if vocab.bare_else_keyword and not has_terminal:
        children = list(node.children)
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
    bool_op_operators: frozenset[str] | None, nested_callables: frozenset[str], content: bytes,
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
            op_text = _bool_op_text(node, content)
            counts = (bool_op_operators is None) or (op_text in bool_op_operators)
            if counts:
                parent = node.parent
                in_continuing = False
                if parent is not None and parent.type == bool_op_node:
                    parent_op = _bool_op_text(parent, content)
                    if (bool_op_operators is None or parent_op in bool_op_operators) and parent_op == op_text:
                        in_continuing = True
                if not in_continuing:
                    cog += 1
        new_depth = depth + 1 if ctype in nesting_nodes else depth
        for child in reversed(node.children):
            stack.append((child, new_depth))
    return cog
