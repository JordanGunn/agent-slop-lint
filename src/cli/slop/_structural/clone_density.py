"""Clone-density kernel — Type-2 clone detection.

Two functions are Type-2 clones when they share the same *structural shape*
(AST node-type sequence) but differ in identifier names and/or literal values.
This catches copy-paste duplication where variable names were renamed but the
algorithm is identical.

Algorithm
---------
1. Enumerate source files via fd.
2. Parse each file with tree-sitter.
3. For every top-level function/method node, walk the body subtree and collect
   the ordered sequence of AST node *types* (leaf nodes only, all text stripped).
   This sequence is the function's structural fingerprint.
4. Hash the fingerprint (SHA-1, first 12 hex chars).
5. Group entries by hash.  Any group with ≥ 2 members is a clone cluster.
6. Return clusters sorted by size descending.

Supported languages: Python, JavaScript, TypeScript, Go, Rust, Java, C#, Julia.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Per-language function-node types (same catalogue as god_module)
# ---------------------------------------------------------------------------

_FUNCTION_NODES: dict[str, frozenset[str]] = {
    "python": frozenset({"function_definition", "async_function_definition"}),
    "javascript": frozenset({
        "function_declaration", "function_expression",
        "arrow_function", "generator_function_declaration",
        "method_definition",
    }),
    "typescript": frozenset({
        "function_declaration", "function_expression",
        "arrow_function", "generator_function_declaration",
        "method_definition", "method_signature",
    }),
    "go": frozenset({"function_declaration", "method_declaration"}),
    "rust": frozenset({"function_item"}),
    "java": frozenset({"method_declaration", "constructor_declaration"}),
    "c_sharp": frozenset({"method_declaration", "constructor_declaration",
                           "local_function_statement"}),
    "julia": frozenset({"function_definition", "short_function_definition"}),
}

_LANG_GLOBS: dict[str, list[str]] = {
    "python":     ["**/*.py"],
    "javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],
    "typescript": ["**/*.ts", "**/*.tsx"],
    "go":         ["**/*.go"],
    "rust":       ["**/*.rs"],
    "java":       ["**/*.java"],
    "c_sharp":    ["**/*.cs"],
    "julia":      ["**/*.jl"],
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CloneEntry:
    """One function that belongs to a clone cluster."""

    file: str       # relative path
    name: str       # function name (or "<anonymous>")
    line: int       # 1-based start line
    end_line: int
    language: str
    fingerprint: str  # 12-char hex hash


@dataclass
class CloneCluster:
    """A group of functions sharing the same structural fingerprint."""

    fingerprint: str
    size: int
    members: list[CloneEntry] = field(default_factory=list)


@dataclass
class CloneDensityResult:
    """Aggregated result from clone_density_kernel."""

    clusters: list[CloneCluster] = field(default_factory=list)
    functions_analyzed: int = 0
    files_searched: int = 0
    clone_fraction: float = 0.0   # fraction of functions in ≥1 clone pair
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_leaf_types(node: object) -> list[str]:
    """DFS walk; yield the type of every leaf node."""
    stack = [node]
    leaves: list[str] = []
    while stack:
        n = stack.pop()
        children = n.children  # type: ignore[attr-defined]
        if children:
            stack.extend(reversed(children))
        else:
            leaves.append(n.type)  # type: ignore[attr-defined]
    return leaves


def _fingerprint(leaf_types: list[str]) -> str:
    h = hashlib.sha1(",".join(leaf_types).encode(), usedforsecurity=False)
    return h.hexdigest()[:12]


def _function_name(node: object, lang: str) -> str:
    """Extract function name from a function-definition node."""
    for child in node.children:  # type: ignore[attr-defined]
        if child.type == "identifier":  # type: ignore[attr-defined]
            return child.text.decode(errors="replace")  # type: ignore[attr-defined]
    return "<anonymous>"


def _body_node(node: object, lang: str) -> object | None:
    """Return the body/block child of a function node (language-specific)."""
    body_types = {
        "python": {"block"},
        "javascript": {"statement_block"},
        "typescript": {"statement_block"},
        "go": {"block"},
        "rust": {"block"},
        "java": {"block"},
        "c_sharp": {"block"},
        "julia": {"block"},
    }
    wanted = body_types.get(lang, {"block"})
    for child in node.children:  # type: ignore[attr-defined]
        if child.type in wanted:  # type: ignore[attr-defined]
            return child
    return node  # fallback: fingerprint the whole node


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def clone_density_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    min_leaf_nodes: int = 10,
    hidden: bool = False,
    no_ignore: bool = False,
) -> CloneDensityResult:
    """Detect structurally identical function bodies (Type-2 clones).

    Args:
        root:           Search root.
        languages:      Restrict to these languages (default: all supported).
        globs:          Include glob patterns.
        excludes:       Exclude patterns.
        min_leaf_nodes: Minimum AST leaf count for a function to be fingerprinted.
                        Very short functions (pass, return x) produce trivial
                        fingerprints that generate many false-positive clusters.
        hidden:         Search hidden files.
        no_ignore:      Ignore .gitignore rules.
    """
    active = (
        {l.lower() for l in languages} & set(_FUNCTION_NODES)
        if languages else set(_FUNCTION_NODES)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])
    ]
    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    # fingerprint → [CloneEntry, ...]
    buckets: dict[str, list[CloneEntry]] = {}
    total_functions = 0
    errors: list[str] = []

    for fp in files:
        lang = detect_language(fp)
        if lang not in active or lang not in _FUNCTION_NODES:
            continue
        func_node_types = _FUNCTION_NODES[lang]
        tree_lang = load_language(lang)
        if tree_lang is None:
            continue
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

            rel = str(fp.relative_to(root))
            _collect_functions(
                tree.root_node, func_node_types, lang, rel,
                buckets, min_leaf_nodes, errors,
            )
            # Count all function nodes in the file (including those skipped for size)
            total_functions += sum(
                1 for node in _iter_nodes(tree.root_node)
                if node.type in func_node_types
            )
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    # Build cluster list — only groups with ≥ 2 members
    clusters = [
        CloneCluster(
            fingerprint=fp_hex,
            size=len(members),
            members=sorted(members, key=lambda e: (e.file, e.line)),
        )
        for fp_hex, members in buckets.items()
        if len(members) >= 2
    ]
    clusters.sort(key=lambda c: -c.size)

    cloned_fns = sum(c.size for c in clusters)
    clone_fraction = cloned_fns / total_functions if total_functions else 0.0

    return CloneDensityResult(
        clusters=clusters,
        functions_analyzed=total_functions,
        files_searched=len(files),
        clone_fraction=clone_fraction,
        errors=errors,
    )


def _iter_nodes(node: object):
    """BFS generator over all nodes in the subtree."""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)  # type: ignore[attr-defined]


def _collect_functions(
    root_node: object,
    func_node_types: frozenset[str],
    lang: str,
    rel: str,
    buckets: dict[str, list[CloneEntry]],
    min_leaf_nodes: int,
    errors: list[str],
) -> None:
    """Walk root_node; fingerprint every function body found."""
    for node in _iter_nodes(root_node):
        if node.type not in func_node_types:  # type: ignore[attr-defined]
            continue
        body = _body_node(node, lang)
        if body is None:
            continue
        leaves = _collect_leaf_types(body)
        if len(leaves) < min_leaf_nodes:
            continue
        fp_hex = _fingerprint(leaves)
        entry = CloneEntry(
            file=rel,
            name=_function_name(node, lang),
            line=node.start_point[0] + 1,  # type: ignore[attr-defined]
            end_line=node.end_point[0] + 1,  # type: ignore[attr-defined]
            language=lang,
            fingerprint=fp_hex,
        )
        buckets.setdefault(fp_hex, []).append(entry)
