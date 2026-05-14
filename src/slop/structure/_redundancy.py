"""Sibling-callee overlap — refactoring signal for top-level functions.

When two sibling top-level functions in the same module call the same
set of helpers, it suggests either (a) a missing shared helper that
should encapsulate the common calls, or (b) a partial copy-paste with
minor variation. Substrate-aligned port of the legacy
``sibling_call_redundancy_kernel``: iterates ``structure.callables()``,
asks each grammar for call-node types and callee extraction, applies
universal filters (length, dunders) plus per-grammar ``trivial_callees``,
and emits ``RedundancyPair`` records.
"""
from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

from slop.structure.records import RedundancyPair
from slop.tree.records import CallableKind

if TYPE_CHECKING:
    from slop.structure.view import Structure
    from slop.tree.records import Callable as _Callable


def compute_redundancy(
    structure: Structure,
    *,
    min_shared: int = 3,
    min_score: float = 0.5,
) -> list[RedundancyPair]:
    """Pair sibling top-level callables by callee-set overlap."""
    by_file: dict[str, list[_Callable]] = {}
    for c in structure.callables():
        if c.kind != CallableKind.FUNCTION:
            continue
        if c.parent and "." in c.parent:
            # Nested function (parent has a dotted qualname) — skip.
            continue
        by_file.setdefault(str(c.path), []).append(c)

    pairs: list[RedundancyPair] = []
    for file_path, callables in by_file.items():
        callees_by_fn: list[tuple[str, int, frozenset[str]]] = []
        for c in callables:
            callees = structure.callees_of(c)
            if not callees:
                continue
            callees_by_fn.append((
                c.qualname.rsplit(".", 1)[-1],
                c.line,
                callees,
            ))

        for (name_a, line_a, set_a), (name_b, line_b, set_b) in combinations(callees_by_fn, 2):
            shared = set_a & set_b
            if len(shared) < min_shared:
                continue
            max_size = max(len(set_a), len(set_b))
            score = len(shared) / max_size
            if score < min_score:
                continue
            pairs.append(RedundancyPair(
                file=file_path,
                fn_a=name_a, fn_b=name_b,
                fn_a_line=line_a, fn_b_line=line_b,
                shared_callees=tuple(sorted(shared)),
                score=round(score, 3),
            ))

    pairs.sort(key=lambda p: -p.score)
    return pairs


def callees_of(structure: Structure, callable_record) -> frozenset[str]:
    """Collect non-trivial callee names appearing in a callable's body.

    Universal filters: length >= 3, no dunder names. Per-grammar
    filters: ``Language.trivial_callees()`` stdlib lists.
    """
    from slop.language.grammars import LANGUAGE_BY_ID

    path_str = str(callable_record.path)
    language = structure._language_by_path.get(path_str)
    if language is None:
        return frozenset()
    lang_cls = LANGUAGE_BY_ID.get(language)
    if lang_cls is None:
        return frozenset()

    call_types = lang_cls.call_node_types()
    if not call_types:
        return frozenset()
    trivial = lang_cls.trivial_callees()

    node = structure._node_by_key.get((path_str, callable_record.qualname))
    if node is None:
        return frozenset()
    content = structure._content_by_key.get((path_str, callable_record.qualname), b"")
    body = node.child_by_field_name("body") or node

    callees: set[str] = set()
    stack = [body]
    while stack:
        n = stack.pop()
        if n.type in call_types:
            name = lang_cls.extract_callee_name(n, content)
            if name is not None and _is_meaningful(name, trivial):
                callees.add(name)
        stack.extend(n.children)
    return frozenset(callees)


def _is_meaningful(name: str, trivial: frozenset[str]) -> bool:
    if len(name) < 3:
        return False
    if name.startswith("__") and name.endswith("__"):
        return False
    if name in trivial:
        return False
    return True
