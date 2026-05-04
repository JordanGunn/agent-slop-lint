"""Sibling call redundancy kernel.

Two top-level functions in the same module that call the same set of helpers
are a refactoring signal: either they should delegate to a shared helper that
encapsulates the common calls, or the two callers should be merged/restructured.

Algorithm
---------
1. For every Python file, enumerate top-level function definitions.
2. For each function, collect the set of identifiers appearing in *call*
   position inside the body (callee names).  Filter out:
   - Python built-ins and standard names (print, len, range, …)
   - Names shorter than 3 characters (likely loop variables / operators)
   - Dunder names (__init__, __repr__, …)
3. For every pair of sibling top-level functions (fn_a, fn_b), compute:
   - shared  = callee_set_a ∩ callee_set_b
   - score   = |shared| / max(|callee_set_a|, |callee_set_b|)
4. Report pairs where |shared| ≥ min_shared (default: 3) OR
   score ≥ min_score (default: 0.5).

Only Python is supported in this release.  Go, Rust and TypeScript can be
added later by extending ``_FUNCTION_NODES`` and ``_gather_callees``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Built-in name filter
# ---------------------------------------------------------------------------

_PYTHON_BUILTINS: frozenset[str] = frozenset({
    "print", "len", "range", "sorted", "reversed", "enumerate", "zip",
    "map", "filter", "any", "all", "sum", "min", "max", "abs", "round",
    "list", "dict", "set", "tuple", "str", "int", "float", "bool",
    "isinstance", "issubclass", "type", "id", "hash", "repr", "getattr",
    "setattr", "hasattr", "delattr", "callable", "iter", "next",
    "open", "input", "super", "vars", "dir", "locals", "globals",
    "staticmethod", "classmethod", "property",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "RuntimeError", "StopIteration", "NotImplementedError",
    "True", "False", "None",
})

_LANG_GLOBS: dict[str, list[str]] = {
    "python": ["**/*.py"],
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SiblingPair:
    """Two sibling top-level functions with overlapping callee sets."""

    file: str
    fn_a: str
    fn_b: str
    fn_a_line: int
    fn_b_line: int
    shared_callees: list[str]
    score: float             # |shared| / max(|callees_a|, |callees_b|)


@dataclass
class SiblingCallResult:
    """Aggregated result from sibling_call_redundancy_kernel."""

    pairs: list[SiblingPair] = field(default_factory=list)
    functions_analyzed: int = 0
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_trivial_callee(name: str) -> bool:
    """True if the callee name should be excluded from the analysis."""
    if name in _PYTHON_BUILTINS:
        return True
    if name.startswith("__") and name.endswith("__"):
        return True
    if len(name) < 3:
        return True
    return False


def _fn_name_from_node(node: object, content: bytes) -> str:
    name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
    return "<anonymous>"


def _gather_callees(body: object, content: bytes) -> set[str]:
    """DFS collect all function call names in a subtree."""
    callees: set[str] = set()
    stack = [body]
    while stack:
        node = stack.pop()
        if node.type == "call":  # type: ignore[attr-defined]
            fn_child = node.child_by_field_name("function")  # type: ignore[attr-defined]
            if fn_child is not None:
                if fn_child.type == "identifier":  # type: ignore[attr-defined]
                    name = content[fn_child.start_byte:fn_child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    if not _is_trivial_callee(name):
                        callees.add(name)
                elif fn_child.type == "attribute":  # type: ignore[attr-defined]
                    attr = fn_child.child_by_field_name("attribute")  # type: ignore[attr-defined]
                    if attr:
                        name = content[attr.start_byte:attr.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                        if not _is_trivial_callee(name):
                            callees.add(name)
        stack.extend(node.children)  # type: ignore[attr-defined]
    return callees


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def sibling_call_redundancy_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    min_shared: int = 3,
    min_score: float = 0.5,
) -> SiblingCallResult:
    """Detect sibling top-level function pairs with high callee overlap.

    Args:
        root:        Search root.
        languages:   Restrict to these languages.
        globs:       Include glob patterns.
        excludes:    Exclude patterns.
        hidden:      Search hidden files.
        no_ignore:   Ignore .gitignore rules.
        min_shared:  Minimum number of shared non-trivial callees to flag.
        min_score:   Minimum overlap ratio to flag.
    """
    active = (
        {l.lower() for l in languages} & set(_LANG_GLOBS)
        if languages else set(_LANG_GLOBS)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])
    ]
    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    pairs: list[SiblingPair] = []
    errors: list[str] = []
    total_functions = 0

    for fp in files:
        lang = detect_language(fp)
        if lang not in active:
            continue
        if lang == "python":
            file_pairs, fn_count, file_errors = _analyze_python_file(
                fp, root, min_shared, min_score
            )
            pairs.extend(file_pairs)
            total_functions += fn_count
            errors.extend(file_errors)

    pairs.sort(key=lambda p: -p.score)
    return SiblingCallResult(
        pairs=pairs,
        functions_analyzed=total_functions,
        files_searched=len(files),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Python implementation
# ---------------------------------------------------------------------------


def _analyze_python_file(
    fp: Path,
    root: Path,
    min_shared: int,
    min_score: float,
) -> tuple[list[SiblingPair], int, list[str]]:
    """Return (sibling_pairs, function_count, errors) for one Python file."""
    tree_lang = load_language("python")
    if tree_lang is None:
        return [], 0, []
    try:
        import tree_sitter
        content = fp.read_bytes()
        try:
            parser = tree_sitter.Parser(tree_lang)
            tree = parser.parse(content)
        except TypeError:
            parser = tree_sitter.Parser()
            parser.language = tree_lang  # type: ignore[assignment]
            tree = parser.parse(content)
    except Exception as exc:
        return [], 0, [f"{fp}: {exc}"]

    rel = str(fp.relative_to(root))
    fn_types = frozenset({"function_definition", "async_function_definition"})

    # Collect top-level function nodes only (direct children of root or class bodies)
    top_level: list[tuple[str, int, set[str]]] = []  # (name, start_line, callees)
    for node in tree.root_node.children:  # type: ignore[attr-defined]
        if node.type in fn_types:  # type: ignore[attr-defined]
            fn_name = _fn_name_from_node(node, content)
            fn_line = node.start_point[0] + 1  # type: ignore[attr-defined]
            body = node.child_by_field_name("body") or node  # type: ignore[attr-defined]
            callees = _gather_callees(body, content)
            top_level.append((fn_name, fn_line, callees))

    pairs: list[SiblingPair] = []
    for (name_a, line_a, callees_a), (name_b, line_b, callees_b) in combinations(top_level, 2):
        if not callees_a or not callees_b:
            continue
        shared = callees_a & callees_b
        if not shared:
            continue
        max_size = max(len(callees_a), len(callees_b))
        score = len(shared) / max_size
        if len(shared) >= min_shared and score >= min_score:
            pairs.append(SiblingPair(
                file=rel,
                fn_a=name_a,
                fn_b=name_b,
                fn_a_line=line_a,
                fn_b_line=line_b,
                shared_callees=sorted(shared),
                score=round(score, 3),
            ))

    return pairs, len(top_level), []
