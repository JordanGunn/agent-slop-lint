"""Per-callable complexity algorithms — cyclomatic, NPath, cognitive.

These three walkers share AST machinery (definition unwrapping, boolean-
operator text extraction) and grew past the inline-on-the-view threshold,
so they live here as a delegated algorithm module. ``Structure``'s
``cyclomatic`` / ``combinatorial`` / ``cognitive`` methods resolve the
AST node, content bytes, and ``Language`` for a callable, then hand off
to the three entry points below.

Per-language node vocabularies all come from the ``Language`` class; a
grammar that declares no decision/structural vocabulary scores the base
path (CCX=1, NP=1, CogC=0).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


# ---- public entry points (view methods delegate here) -------------------

def cyclomatic(node: Any, content: bytes, lang: Any) -> int:
    """McCabe cyclomatic complexity for one callable (McCabe 1976).

    Counts decision points + short-circuit boolean operators, plus 1 for
    the base path. Grammars without ``decision_nodes`` score CCX=1.
    """
    decision_nodes = lang.decision_nodes()
    if not decision_nodes:
        return 1
    walk_from = resolve_body(node, lang.definition_unwrap_types())
    count = _count_decisions(
        walk_from,
        decision_nodes,
        lang.boolean_op_node(),
        lang.boolean_op_operators(),
        lang.callable(),
        content,
    )
    return count + 1


def cognitive(node: Any, content: bytes, lang: Any) -> int:
    """Cognitive Complexity for one callable (Campbell 2018).

    Adds a nesting penalty to each decision, discounts compensating
    decisions, and collapses same-operator boolean chains. Grammars
    without ``decision_nodes`` score CogC=0.
    """
    decision_nodes = lang.decision_nodes()
    if not decision_nodes:
        return 0
    walk_from = resolve_body(node, lang.definition_unwrap_types())
    return _cognitive_walk(
        walk_from,
        decision_nodes,
        lang.nesting_nodes(),
        lang.compensating_decisions(),
        lang.boolean_op_node(),
        lang.boolean_op_operators(),
        lang.callable(),
        content,
    )


def combinatorial(node: Any, lang: Any) -> int:
    """NPath — acyclic execution-path count for one callable (Nejmeh 1988).

    Multiplicative over sequential branching structures. Grammars without
    a structural vocabulary score NP=1.
    """
    vocab = _NPathVocab.for_language(lang)
    node = _unwrap_definition(node, vocab.definition_unwrap_types)
    return max(1, _npath_walk(node, vocab))


# ---- shared AST helpers -------------------------------------------------

def _unwrap_definition(node: Any, unwrap: frozenset[str]) -> Any:
    """Descend through wrapper nodes (e.g. C++ ``template_declaration``)
    to the actual definition. Fixed-depth guard against malformed ASTs.
    """
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
    """Unwrap to the definition then descend to its ``body`` field.

    Falls back to the unwrapped node when no body field exists. Public
    because the Halstead rule walks the same resolved body subtree.
    """
    current = _unwrap_definition(node, unwrap)
    body = current.child_by_field_name("body")
    return body if body is not None else current


def _bool_op_text(node: Any, content: bytes) -> str:
    """Extract the operator text from a boolean/binary operator node.

    Tree-sitter grammars expose the operator in four shapes:
      1. As an ``operator`` field on the binary node (JS/TS/Go/Java/C#/C/C++).
      2. As a named child node of type ``operator`` (Julia, Ruby).
      3. As a child whose type name IS the operator keyword (Python:
         ``and`` / ``or`` / ``not``).
      4. As an unnamed punctuation token between operands.

    Returns the operator text or ``""`` if no operator child can be found.
    """
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


def _bool_op_matches(
    node: Any,
    operators: frozenset[str],
    content: bytes,
) -> bool:
    """True if ``node``'s operator text is in ``operators``."""
    op_text = _bool_op_text(node, content)
    return op_text in operators if op_text else False


# ---- cyclomatic ---------------------------------------------------------

def _count_decisions(
    node: Any,
    decision_nodes: frozenset[str],
    bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None,
    nested_callables: frozenset[str],
    content: bytes,
) -> int:
    """Recursively count cyclomatic decision points under ``node``.

    ``nested_callables`` is the per-language set of node types that
    define a new callable scope (i.e. ``Language.callable()``). The
    walk does not descend into nested callables — each callable's
    metric is body-local. Honours per-language short-circuit operator
    filtering: when ``bool_op_operators`` is None, every
    ``bool_op_node`` instance counts (Python's dedicated
    ``boolean_operator``); when non-None, only nodes whose operator
    text is in the set count (C-family ``binary_expression`` with
    ``&&``/``||``/``??``).
    """
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


# ---- combinatorial (NPath) ----------------------------------------------

@dataclass(frozen=True)
class _NPathVocab:
    """Per-language vocabulary bundle for the combinatorial walker.

    Pulled together from the ``Language`` class once per
    ``combinatorial`` call to avoid threading 13 separate arguments
    through the recursive helpers below.
    """
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
    def for_language(cls, lang: Any) -> _NPathVocab:
        return cls(
            if_nodes=lang.if_nodes(),
            elif_nodes=lang.elif_nodes(),
            else_nodes=lang.else_nodes(),
            loop_nodes=lang.loop_nodes(),
            switch_nodes=lang.switch_nodes(),
            case_nodes=lang.case_nodes(),
            try_nodes=lang.try_nodes(),
            catch_nodes=lang.catch_nodes(),
            body_field=lang.body_field(),
            block_types=lang.block_types(),
            switch_body_types=lang.switch_body_types(),
            body_skip_types=lang.body_skip_types(),
            bare_else_keyword=lang.bare_else_keyword(),
            nested_callables=lang.callable(),
            definition_unwrap_types=lang.definition_unwrap_types(),
        )


def _npath_walk(callable_node: Any, vocab: _NPathVocab) -> int:
    """Compute NPath of a callable definition's body.

    For grammars with a body field (most), descends into the field
    and walks it as a sequence of statements. For flat-body grammars
    (Julia, Ruby), walks the callable's direct children filtering by
    ``body_skip_types``.
    """
    if vocab.body_field:
        body = callable_node.child_by_field_name(vocab.body_field)
        if body is None:
            return 1
        return _npath_of_block(body, vocab)
    return _npath_of_flat_body(callable_node, vocab)


def _npath_of_block(node: Any, vocab: _NPathVocab) -> int:
    """NP of a sequence of statements.

    If ``node`` is itself a block wrapper, multiplies its children's
    NPs; otherwise treats ``node`` as a single statement.
    """
    if node is None:
        return 1
    if node.type in vocab.block_types:
        result = 1
        for child in node.children:
            result *= _npath_of_node(child, vocab)
        return result
    return _npath_of_node(node, vocab)


def _npath_of_flat_body(node: Any, vocab: _NPathVocab) -> int:
    """NP of a flat-body construct (Julia, Ruby).

    Walks direct children, skipping structural-keyword node types
    enumerated in ``body_skip_types``, and multiplies non-trivial NPs.
    """
    result = 1
    for child in node.children:
        if child.type in vocab.body_skip_types:
            continue
        cn = _npath_of_node(child, vocab)
        if cn > 1:
            result *= cn
    return result


def _npath_of_node(node: Any, vocab: _NPathVocab) -> int:
    """Dispatch NP contribution of a single AST node by its structural role."""
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

    # Nested callable: each has its own metric — do not descend.
    if ntype in vocab.nested_callables:
        return 1

    # Generic compound: walk through, multiplying non-trivial children.
    result = 1
    for child in node.children:
        cn = _npath_of_node(child, vocab)
        if cn > 1:
            result *= cn
    return result


def _npath_of_switch(node: Any, vocab: _NPathVocab) -> int:
    """NP of a switch/match — sum of case NPs (>= 1).

    Some grammars (Java ``switch_block`` / C# ``switch_body`` / C/C++
    ``compound_statement``) wrap cases inside an intermediate block;
    ``switch_body_types`` tells the walker to recurse through them.
    """
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
    """NP of a try/catch — try-body NP + sum of catch-body NPs."""
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
    if handler_sum == 0:
        return try_body_np
    return try_body_np + handler_sum


def _npath_of_if(node: Any, vocab: _NPathVocab) -> int:
    """NP of an if/elif/else chain — sum of branch NPs.

    Adds +1 for an implicit fall-through path when no terminal
    ``else`` is present. Handles three else shapes:
      - else-clause wrapper (Python, Ruby, Java, C, C++, Go, ...)
      - bare ``else`` keyword followed by a block (C#)
      - C-style ``else { if … }`` nested chains
    """
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
                    alt_nps.append(_npath_of_block(ec, vocab))
                    else_added = True
                elif ec.type in vocab.if_nodes:
                    # C-style else-if chain
                    alt_nps.append(_npath_of_if(ec, vocab))
                    else_added = True
            if not else_added and not vocab.body_field:
                # Flat-body langs (Julia): else_clause has no block
                # wrapper; treat as +1 path. Nested control flow
                # inside the else is not deeply analysed (documented
                # limitation, inherited from the legacy kernel).
                alt_nps.append(1)

    # Bare-keyword else (C#): "else" keyword child followed by a block
    # or nested if_statement as the next sibling.
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


# ---- cognitive ----------------------------------------------------------

def _cognitive_walk(
    root: Any,
    decision_nodes: frozenset[str],
    nesting_nodes: frozenset[str],
    compensating: frozenset[str],
    bool_op_node: str | None,
    bool_op_operators: frozenset[str] | None,
    nested_callables: frozenset[str],
    content: bytes,
) -> int:
    """Walk ``root`` accumulating Cognitive Complexity (Campbell 2018).

    Iterative stack walk where each entry carries the current nesting
    depth. Each decision node contributes ``1 + depth``; compensating
    decisions contribute ``1 + max(0, depth - 1)``. Short-circuit
    operators count +1 unless they're continuing a same-operator chain
    with their syntactic parent (tree-sitter ``node.parent``).
    """
    cog = 0
    stack: list[tuple[Any, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        ctype = node.type

        # Skip nested callables; each gets its own metric.
        if ctype in nested_callables and node is not root:
            continue

        # Decision contribution.
        if ctype in decision_nodes:
            if ctype in compensating:
                cog += 1 + max(0, depth - 1)
            else:
                cog += 1 + depth

        # Boolean operator with sequence collapsing.
        if bool_op_node is not None and ctype == bool_op_node:
            op_text = _bool_op_text(node, content)
            counts = (bool_op_operators is None) or (op_text in bool_op_operators)
            if counts:
                parent = node.parent
                in_continuing_sequence = False
                if parent is not None and parent.type == bool_op_node:
                    parent_op = _bool_op_text(parent, content)
                    parent_counts = (
                        bool_op_operators is None or parent_op in bool_op_operators
                    )
                    if parent_counts and parent_op == op_text:
                        in_continuing_sequence = True
                if not in_continuing_sequence:
                    cog += 1

        # Children inherit incremented depth if this node is a nester.
        new_depth = depth + 1 if ctype in nesting_nodes else depth
        for child in reversed(node.children):
            stack.append((child, new_depth))

    return cog
