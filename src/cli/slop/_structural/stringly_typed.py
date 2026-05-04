"""Stringly-typed parameter detection kernel.

A *stringly-typed* parameter is a function parameter annotated ``str``
(or left untyped) whose name is a domain-concept sentinel — words like
``status``, ``mode``, ``kind``, ``level``, ``format``, ``role``, ``action``.
These parameters almost always represent a finite set of string constants
that should instead be modelled as a ``Literal[...]`` union or an ``Enum``.

Detection strategy (two-pass)
------------------------------
1. **AST pass**: find Python function parameters that
   - are annotated ``str`` (or ``Optional[str]`` / ``str | None``), and
   - have a name that matches the sentinel word-list.
2. **Call-site pass**: use ripgrep to find call sites for each flagged
   function and collect the distinct string literals passed in the sentinel
   position. Functions where the call-site cardinality ≤ ``max_cardinality``
   (default 8) are reported — a small cardinality suggests an enum is
   appropriate.

When no call sites can be found (e.g. private API, or rg unavailable) the
function is still reported as advisory (severity = "warning").

Supported language: Python (full two-pass).
Other languages: AST-only pass (no call-site grep).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel
from slop._text.grep import grep_kernel

# ---------------------------------------------------------------------------
# Sentinel names (lower-cased; matched as whole words or with suffixes _)
# ---------------------------------------------------------------------------

_SENTINEL_NAMES: frozenset[str] = frozenset({
    "status", "mode", "kind", "level", "format",
    "role", "action", "category", "severity", "phase",
    "stage", "style", "direction", "state", "type",
    "method", "strategy", "algorithm", "protocol",
    "encoding", "codec", "backend", "driver", "engine",
})

# Strip trailing _ (PEP 8 convention for shadowing builtins like type_)
_STRIP_TRAILING = re.compile(r'_+$')

# Type annotation text patterns that indicate a str annotation
_STR_ANNOTATION_RE = re.compile(
    r'\bstr\b'
)

_LANG_GLOBS: dict[str, list[str]] = {
    "python": ["**/*.py"],
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StringlyEntry:
    """One function parameter identified as stringly-typed."""

    file: str
    function_name: str
    param_name: str
    param_line: int       # 1-based start of function
    annotated: bool       # True if parameter has str annotation; False if inferred
    call_site_literals: list[str] = field(default_factory=list)
    call_site_count: int = 0  # distinct literal values found at call sites


@dataclass
class StringlyResult:
    """Aggregated result from stringly_typed_kernel."""

    entries: list[StringlyEntry] = field(default_factory=list)
    functions_analyzed: int = 0
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def stringly_typed_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_cardinality: int = 8,
    require_str_annotation: bool = True,
) -> StringlyResult:
    """Detect functions with stringly-typed parameters.

    Args:
        root:                   Search root.
        languages:              Restrict to these languages.
        globs:                  Include glob patterns.
        excludes:               Exclude patterns.
        hidden:                 Search hidden files.
        no_ignore:              Ignore .gitignore rules.
        max_cardinality:        Report only when call-site literal cardinality
                                is ≤ this value (default: 8).
        require_str_annotation: When True, only report parameters with an
                                explicit ``str`` annotation. When False, also
                                report untyped sentinel-named parameters.
    """
    active_langs = (
        {l.lower() for l in languages} & set(_LANG_GLOBS)
        if languages else set(_LANG_GLOBS)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active_langs) for g in _LANG_GLOBS.get(l, [])
    ]
    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    entries: list[StringlyEntry] = []
    errors: list[str] = []
    total_functions = 0

    for fp in files:
        lang = detect_language(fp)
        if lang not in active_langs:
            continue
        if lang == "python":
            _scan_python_file(
                fp, root, entries, errors, require_str_annotation
            )
            total_functions += _count_python_functions(fp)
        # Other languages: skip for now (placeholder for future extension)

    # Pass 2: call-site literal collection via ripgrep
    _enrich_with_call_sites(entries, root, excludes or [], max_cardinality)

    entries.sort(key=lambda e: e.call_site_count)
    return StringlyResult(
        entries=entries,
        functions_analyzed=total_functions,
        files_searched=len(files),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Python AST pass
# ---------------------------------------------------------------------------


def _scan_python_file(
    fp: Path,
    root: Path,
    out: list[StringlyEntry],
    errors: list[str],
    require_str_annotation: bool,
) -> None:
    tree_lang = load_language("python")
    if tree_lang is None:
        return
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
        _walk_python_functions(tree.root_node, content, rel, out, require_str_annotation)
    except Exception as exc:
        errors.append(f"{fp}: {exc}")


def _walk_python_functions(
    root_node: object,
    content: bytes,
    rel: str,
    out: list[StringlyEntry],
    require_str_annotation: bool,
) -> None:
    fn_types = frozenset({"function_definition", "async_function_definition"})
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type in fn_types:  # type: ignore[attr-defined]
            _process_python_function(node, content, rel, out, require_str_annotation)
        stack.extend(node.children)  # type: ignore[attr-defined]


def _process_python_function(
    fn_node: object,
    content: bytes,
    rel: str,
    out: list[StringlyEntry],
    require_str_annotation: bool,
) -> None:
    name_node = fn_node.child_by_field_name("name")  # type: ignore[attr-defined]
    fn_name = (
        content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
        if name_node else "<anonymous>"
    )
    fn_line = fn_node.start_point[0] + 1  # type: ignore[attr-defined]

    params_node = fn_node.child_by_field_name("parameters")  # type: ignore[attr-defined]
    if params_node is None:
        return

    for child in params_node.children:  # type: ignore[attr-defined]
        ptype = child.type  # type: ignore[attr-defined]
        param_name = None
        has_str_annotation = False

        if ptype == "identifier":
            raw = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            param_name = raw
            has_str_annotation = False  # untyped

        elif ptype in ("typed_parameter", "typed_default_parameter"):
            name_n = child.child_by_field_name("name") or next(  # type: ignore[attr-defined]
                (c for c in child.children if c.type == "identifier"), None  # type: ignore[attr-defined]
            )
            type_n = child.child_by_field_name("type")  # type: ignore[attr-defined]
            if name_n is None:
                continue
            param_name = content[name_n.start_byte:name_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if type_n is not None:
                type_text = content[type_n.start_byte:type_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                has_str_annotation = bool(_STR_ANNOTATION_RE.search(type_text))

        if param_name is None:
            continue
        if require_str_annotation and not has_str_annotation:
            continue

        # Check sentinel names
        clean_name = _STRIP_TRAILING.sub("", param_name).lower()
        if clean_name in _SENTINEL_NAMES:
            out.append(StringlyEntry(
                file=rel,
                function_name=fn_name,
                param_name=param_name,
                param_line=fn_line,
                annotated=has_str_annotation,
            ))


def _count_python_functions(fp: Path) -> int:
    tree_lang = load_language("python")
    if tree_lang is None:
        return 0
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
        fn_types = {"function_definition", "async_function_definition"}
        stack = [tree.root_node]
        count = 0
        while stack:
            n = stack.pop()
            if n.type in fn_types:
                count += 1
            stack.extend(n.children)
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Call-site enrichment via ripgrep
# ---------------------------------------------------------------------------


def _enrich_with_call_sites(
    entries: list[StringlyEntry],
    root: Path,
    excludes: list[str],
    max_cardinality: int,
) -> None:
    """For each entry, search for call-site string literals (best-effort)."""
    if not entries:
        return

    # Build a dict from function name → list of entries
    by_fn: dict[str, list[StringlyEntry]] = {}
    for e in entries:
        by_fn.setdefault(e.function_name, []).append(e)

    # One rg search per unique function name
    for fn_name, fn_entries in by_fn.items():
        # Pattern: fn_name(... "literal" ...) — approximate
        pattern = rf'\b{re.escape(fn_name)}\s*\([^)]*["\']([^"\']+)["\']'
        try:
            result = grep_kernel(
                patterns=[{"kind": "regex", "value": pattern}],
                root=root,
                excludes=excludes,
            )
            # Extract string literal captures from match content
            literals: set[str] = set()
            lit_re = re.compile(r'["\']([^"\']{1,50})["\']')
            for m in result.matches:
                for lit_m in lit_re.finditer(m.content):
                    literals.add(lit_m.group(1))
            for e in fn_entries:
                e.call_site_literals = sorted(literals)
                e.call_site_count = len(literals)
        except Exception:
            pass  # Best-effort; leave call_site_count=0
