"""Imports compute — extract per-file import edges and resolve them.

Per-grammar tree-sitter queries (declared on ``Language.import_queries``)
run against each parsed file's root node; captured module strings become
``Import`` records. A separate resolution step uses the corpus's
module-name index to convert raw module strings into file→file edges.

No regex fallback: files that fail to parse never reach the view, so
they contribute zero edges.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.structure.records import DependencyGraph, Import

if TYPE_CHECKING:
    from slop.tree.records import ParseResult


_MODULE_STRIP_CHARS = "\"'<>"


_NON_MODULE_LEVEL_PARENTS = frozenset({
    "function_definition",
    "decorated_definition",
})


def _is_module_level(node) -> bool:
    """True if the import node sits at module scope (not local or TYPE_CHECKING-guarded)."""
    current = node.parent
    while current is not None:
        ntype = current.type
        if ntype in _NON_MODULE_LEVEL_PARENTS:
            return False
        if ntype == "if_statement":
            cond = current.child_by_field_name("condition")
            if (
                cond is not None
                and cond.type == "identifier"
                and cond.text == b"TYPE_CHECKING"
            ):
                return False
        current = current.parent
    return True


def extract_imports(parses) -> list[Import]:
    """Run each parse's grammar import queries against its root node.

    Returns one ``Import`` per ``@module`` capture across all files.
    Only module-level imports are included — ``TYPE_CHECKING``-guarded
    and function-local imports are excluded since they do not create
    runtime dependency edges.
    """
    from slop.language.grammars import LANGUAGE_BY_ID

    out: list[Import] = []
    for p in parses:
        if p.root_node is None:
            continue
        lang_cls = LANGUAGE_BY_ID.get(p.language)
        if lang_cls is None:
            continue
        queries = lang_cls.import_queries()
        if not queries:
            continue
        ts_lang = lang_cls.grammar()
        for query_str, kind in queries:
            for module, line, node in _run_query(ts_lang, query_str, p.root_node, p.content):
                if not _is_module_level(node):
                    continue
                cleaned = module.strip(_MODULE_STRIP_CHARS)
                if not cleaned:
                    continue
                out.append(Import(file=str(p.path), module=cleaned, kind=kind, line=line))
    return out


def _run_query(ts_lang, query_str: str, root_node, content: bytes):
    """Execute one query against a pre-parsed root; yield (text, line, node) per @module capture.

    Handles both the modern (tree-sitter >= 0.25) ``Query`` + ``QueryCursor``
    API and the legacy ``lang.query()`` API.
    """
    import tree_sitter

    query_cls = getattr(tree_sitter, "Query", None)
    cursor_cls = getattr(tree_sitter, "QueryCursor", None)
    if query_cls is not None and cursor_cls is not None:
        query = query_cls(ts_lang, query_str)
        cursor = cursor_cls(query)
        for _idx, captures in cursor.matches(root_node):
            yield from _module_captures(captures, content)
        return

    # Legacy API
    query = ts_lang.query(query_str)
    for match in query.matches(root_node):
        if isinstance(match, tuple) and len(match) == 2:
            _idx, captures = match
            yield from _module_captures(captures, content)


def _module_captures(captures, content: bytes):
    """Yield (text, line, node) for every capture named ``@module``.

    Tree-sitter's match payload comes back either as a dict
    (``{capture_name: [nodes]}``) or as a list of (capture_name, node)
    pairs depending on the API version. Handle both.
    """
    if isinstance(captures, dict):
        nodes = captures.get("module", [])
        for node in nodes:
            yield _node_text(node, content), node.start_point[0] + 1, node
        return
    # Legacy: list[(name, node)]
    for name, node in captures:
        if name == "module":
            yield _node_text(node, content), node.start_point[0] + 1, node


def _node_text(node, content: bytes) -> str:
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


# ---- Resolution -----------------------------------------------------


def build_module_index(parses) -> dict[str, str]:
    """Build a flat module-name → abs-path index from the corpus.

    For each parsed file, register every "module name" form a grammar
    might emit: the dotted name (``foo.bar``), the slash name
    (``foo/bar``), the bare stem (``bar``), the full filename
    (``bar.py``), and — for Python ``__init__.py`` — the parent
    package name.

    ``first-wins`` semantics: collisions are resolved by registration
    order (driven by the parse order from ``Tree.scan``).
    """
    index: dict[str, str] = {}
    for p in parses:
        fp = Path(p.path)
        fp_str = str(fp)
        for name in _module_names_for_path(fp):
            index.setdefault(name, fp_str)
    return index


def _module_names_for_path(fp: Path) -> list[str]:
    """All module-name spellings a grammar might emit for this path.

    Includes:
      - ``fp.stem`` (bare file stem)
      - ``fp.name`` (filename with extension — for C/C++ ``#include "foo.h"``)
      - dotted and slashed path forms (without extension) of the
        parts trailing the deepest non-source-tree component
      - parent-package forms for ``__init__.py``

    We don't have access to a corpus root here; the resolved-edges
    layer compares the produced names against grammar-emitted module
    strings, and the default ``Language.resolve_module`` falls back
    to trailing-segment matching which handles the common case.
    """
    names: list[str] = [fp.stem, fp.name]
    parts = fp.with_suffix("").parts
    if parts:
        # Trailing-N segment dotted/slashed forms for the last few parts —
        # enough to catch ``foo.bar`` style imports against a file at
        # ``.../foo/bar.py`` without needing the corpus root.
        for take in range(2, min(len(parts), 6) + 1):
            tail = parts[-take:]
            names.append(".".join(tail))
            names.append("/".join(tail))
    if fp.name == "__init__.py" and len(parts) >= 2:
        # ``foo/bar/__init__.py`` → ``foo.bar`` / ``bar`` / etc.
        package_parts = parts[:-1]
        names.append(".".join(package_parts))
        names.append("/".join(package_parts))
        for take in range(1, min(len(package_parts), 5) + 1):
            tail = package_parts[-take:]
            names.append(".".join(tail))
            names.append("/".join(tail))
    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def detect_cycles(graph: DependencyGraph) -> list[list[str]]:
    """Tarjan SCC (Tarjan 1972) over a resolved dependency graph.

    Returns each strongly connected component with more than one node
    as a sorted list of absolute paths. Self-loops (a file that imports
    itself) are excluded by the resolver before reaching this layer.

    The recursive form is fine for typical codebases (a few thousand
    files); for pathological cases switch to an explicit-stack version.
    """
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in sorted(graph.efferent.get(node, frozenset())):
            if neighbor not in indexes:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[neighbor])

        if lowlinks[node] == indexes[node]:
            component: list[str] = []
            while stack:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            if len(component) > 1:
                cycles.append(sorted(component))

    for node in graph.efferent:
        if node not in indexes:
            strongconnect(node)

    return cycles


def build_dependency_graph(parses, imports: list[Import]) -> DependencyGraph:
    """Resolve raw imports to file→file edges.

    Uses each parse's grammar's ``resolve_module`` classmethod to map
    module strings to absolute file paths. Unresolved modules are
    dropped silently. Self-edges (a file importing itself) are also
    dropped.
    """
    from slop.language.grammars import LANGUAGE_BY_ID

    index = build_module_index(parses)
    file_paths = {str(p.path) for p in parses}
    language_by_file = {str(p.path): p.language for p in parses}

    efferent: dict[str, set[str]] = {f: set() for f in file_paths}
    for imp in imports:
        if imp.file not in efferent:
            continue
        lang_id = language_by_file.get(imp.file)
        if lang_id is None:
            continue
        lang_cls = LANGUAGE_BY_ID.get(lang_id)
        if lang_cls is None:
            continue
        resolved = lang_cls.resolve_module(imp.module, index)
        if resolved and resolved != imp.file and resolved in file_paths:
            efferent[imp.file].add(resolved)

    afferent: dict[str, set[str]] = {f: set() for f in file_paths}
    for src, targets in efferent.items():
        for tgt in targets:
            afferent[tgt].add(src)

    return DependencyGraph(
        efferent={f: frozenset(t) for f, t in efferent.items()},
        afferent={f: frozenset(t) for f, t in afferent.items()},
    )
