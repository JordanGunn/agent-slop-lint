"""Identifier-singletons kernel — flag functions where most named locals
appear exactly once after assignment.

Six fresh names, none reused, signals the agent reflex of giving every
intermediate value a name "in case it's needed later." If `user` carried
through, the verbs would do the work.

Detection: walk a function body, find local *bindings* (assignments
to a bare identifier), count subsequent right-hand-side references
to each. Compute the fraction of locals with use-count == 1. If the
fraction exceeds the threshold, flag.

See ``docs/backlog/01.md`` item 6.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._lexical._naming import enumerate_functions


@dataclass
class SingletonHit:
    function: str
    file: str
    line: int
    language: str
    locals_count: int
    singleton_locals: list[str]
    singleton_fraction: float


@dataclass
class IdentifierSingletonsResult:
    items: list[SingletonHit] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


def identifier_singletons_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_locals: int = 4,
    max_singleton_fraction: float = 0.6,
) -> IdentifierSingletonsResult:
    """Walk every Python function body; flag functions whose local
    bindings are mostly used exactly once.

    Initial implementation covers Python only — Python has the
    cleanest binding semantics (assignment statement = local binding).
    Other languages need per-language handling for ``let``/``var``/
    ``const`` and that's a deliberate follow-up.
    """
    items: list[SingletonHit] = []
    files_set: set[str] = set()
    fn_count = 0

    for ctx in enumerate_functions(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        fn_count += 1
        files_set.add(ctx.file)
        if ctx.language != "python":
            continue
        if ctx.body_node is None or ctx.name.startswith("<"):
            continue

        bindings = _collect_python_bindings(ctx)
        if len(bindings) < min_locals:
            continue

        use_counts = _count_uses(ctx, set(bindings.keys()))

        # Returned identifiers don't count as singletons (returning a
        # named expression is fine; the rule targets the *write-once-
        # read-once-then-discard* pattern, not "named return").
        returned = _collect_returns(ctx)

        singleton_locals = sorted(
            name for name in bindings
            if use_counts.get(name, 0) == 1 and name not in returned
        )
        if not singleton_locals:
            continue

        fraction = len(singleton_locals) / len(bindings)
        if fraction > max_singleton_fraction:
            items.append(SingletonHit(
                function=ctx.name, file=ctx.file, line=ctx.line,
                language=ctx.language,
                locals_count=len(bindings),
                singleton_locals=singleton_locals,
                singleton_fraction=round(fraction, 3),
            ))

    return IdentifierSingletonsResult(
        items=items,
        files_searched=len(files_set),
        functions_analyzed=fn_count,
        errors=[],
    )


# ---------------------------------------------------------------------------
# Python helpers
# ---------------------------------------------------------------------------


def _collect_python_bindings(ctx) -> dict[str, int]:
    """Return ``{name: line}`` for each bare-identifier assignment in
    the function body. Multi-target assignments (``a, b = ...``) are
    walked into. Augmented assignments (``+=``) are *not* bindings —
    they require the name to already exist."""
    bindings: dict[str, int] = {}

    def walk(node):
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            if left is not None:
                _record_targets(left, ctx.content, bindings, node.start_point[0] + 1)
        # Don't descend into nested function/class scopes
        if node.type in ("function_definition", "class_definition", "lambda"):
            return
        for child in node.children:
            walk(child)

    walk(ctx.body_node)
    return bindings


def _record_targets(node, content: bytes, bindings: dict[str, int], line: int) -> None:
    if node.type == "identifier":
        text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        if text and not text.startswith("_") and text not in bindings:
            bindings[text] = line
    elif node.type in ("pattern_list", "tuple_pattern", "list_pattern"):
        for child in node.children:
            _record_targets(child, content, bindings, line)


def _count_uses(ctx, names: set[str]) -> dict[str, int]:
    """Count identifier occurrences in the function body, EXCLUDING the
    LHS of bindings. Each non-LHS reference to a tracked name
    increments its count."""
    counts: dict[str, int] = {n: 0 for n in names}

    def walk(node, in_lhs: bool):
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None:
                walk(left, in_lhs=True)
            if right is not None:
                walk(right, in_lhs=False)
            return
        if node.type == "identifier" and not in_lhs and node.child_count == 0:
            text = ctx.content[node.start_byte:node.end_byte].decode(
                "utf-8", errors="replace",
            )
            if text in counts:
                counts[text] += 1
            return
        if node.type in ("function_definition", "class_definition", "lambda"):
            return
        for child in node.children:
            walk(child, in_lhs)

    walk(ctx.body_node, in_lhs=False)
    return counts


def _collect_returns(ctx) -> set[str]:
    """Set of bare-identifier names appearing in ``return X`` statements."""
    returned: set[str] = set()

    def walk(node):
        if node.type == "return_statement":
            for child in node.children:
                if child.type == "identifier":
                    text = ctx.content[child.start_byte:child.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    returned.add(text)
            return
        if node.type in ("function_definition", "class_definition", "lambda"):
            return
        for child in node.children:
            walk(child)

    walk(ctx.body_node)
    return returned
