"""Complexity walkers — compute structural primitives from an AST node + grammar.

These read the grammar's control-flow node-type metadata (the tabular adapter)
and walk a single callable's subtree. The primitive for a Callable excludes
nested callables (closures/local defs) — those are separate components counted
separately, so container aggregates sum each leaf exactly once.
"""
from __future__ import annotations

from typing import Any


def cyclomatic(node: Any, grammar: type) -> int:
    """McCabe (1976) cyclomatic complexity of one callable body.

    1 + one per decision node + one per short-circuit boolean operator. Does not
    descend into nested callables.
    """
    decisions = grammar.decision_nodes()
    bool_node = grammar.boolean_op_node()
    bool_ops = grammar.boolean_op_operators()
    callable_types = grammar.callable()

    count = 1
    stack = list(node.children)
    while stack:
        n = stack.pop()
        if n.type in callable_types:
            continue  # nested callable — its own component, don't count here
        if n.type in decisions:
            count += 1
        if bool_node is not None and n.type == bool_node:
            if bool_ops is None:
                count += 1
            else:
                count += sum(1 for c in n.children if c.type in bool_ops)
        stack.extend(n.children)
    return count
