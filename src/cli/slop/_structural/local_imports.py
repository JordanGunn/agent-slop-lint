"""Local import detection kernel.

Detects import statements nested inside function / method bodies.
Module-level imports are the expected location; function-scoped imports
hide dependencies from static analysis (including slop's own deps kernel)
and impose a repeated loading cost in hot paths.

AST tier  — Python, Julia (tree-sitter).
Text tier — Rust (indentation heuristic; tree-sitter not wired for imports).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Per-language tables
# ---------------------------------------------------------------------------

#: Node types that represent an import statement in the AST.
IMPORT_NODE_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"import_statement", "import_from_statement"}),
    "julia":  frozenset({"import_statement", "using_statement"}),
    "c":      frozenset({"preproc_include"}),
    "cpp":    frozenset({"preproc_include", "using_declaration"}),
}

#: Node types that constitute a function / method boundary.
FUNCTION_NODE_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"function_definition"}),
    "julia":  frozenset({"function_definition", "arrow_function_expression"}),
    "c":      frozenset({"function_definition"}),
    "cpp":    frozenset({"function_definition", "lambda_expression"}),
}

#: Extension → language for discovery.
_EXT_MAP: dict[str, str] = {
    ".py": "python",
    ".jl": "julia",
    ".rs": "rust",
    ".c":  "c",
    ".h":  "c",
    ".cpp": "cpp",
    ".cc":  "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class LocalImport:
    """A single function-scoped import."""

    file: str       # absolute path
    line: int       # 1-based
    module: str     # raw import text (first line, trimmed)
    function: str   # enclosing function name or "<anonymous>"
    language: str


@dataclass
class LocalImportsResult:
    """Aggregated result from local_imports_kernel."""

    local_imports: list[LocalImport] = field(default_factory=list)
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def local_imports_kernel(
    root: Path,
    *,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
) -> LocalImportsResult:
    """Detect import statements nested inside function bodies.

    Args:
        root:      Search root.
        globs:     Include glob patterns.
        excludes:  Exclude patterns.
        hidden:    Search hidden files.
        no_ignore: Ignore .gitignore rules.
    """
    find_result = find_kernel(root=root, globs=globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    local_imports: list[LocalImport] = []
    errors: list[str] = []

    for fp in files:
        lang = _EXT_MAP.get(fp.suffix.lower())
        if lang is None:
            continue
        try:
            if lang in IMPORT_NODE_TYPES:
                found = _scan_ast(fp, lang)
            elif lang == "rust":
                found = _scan_rust_text(fp)
            else:
                continue
            local_imports.extend(found)
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    return LocalImportsResult(
        local_imports=local_imports,
        files_searched=len(files),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# AST tier (Python, Julia)
# ---------------------------------------------------------------------------


def _scan_ast(fp: Path, language: str) -> list[LocalImport]:
    """Walk the tree-sitter AST and collect imports inside function bodies."""
    from slop._ast.treesitter import load_language
    import tree_sitter

    lang = load_language(language)
    if lang is None:
        return []

    content = fp.read_bytes()
    try:
        parser = tree_sitter.Parser(lang)
        tree = parser.parse(content)
    except TypeError:
        # Modern API: no-arg constructor + .language attribute
        parser = tree_sitter.Parser()
        parser.language = lang  # type: ignore[assignment]
        tree = parser.parse(content)

    import_types = IMPORT_NODE_TYPES[language]
    function_types = FUNCTION_NODE_TYPES[language]
    results: list[LocalImport] = []
    _walk(tree.root_node, content, str(fp), language, import_types, function_types, results)
    return results


def _walk(
    node: object,
    content: bytes,
    file: str,
    language: str,
    import_types: frozenset[str],
    function_types: frozenset[str],
    out: list[LocalImport],
) -> None:
    """Depth-first AST walk; emit a LocalImport for each function-nested import node."""
    node_type = node.type  # type: ignore[attr-defined]
    if node_type in import_types:
        func_node = _enclosing_function(node, function_types)
        if func_node is not None:
            out.append(LocalImport(
                file=file,
                line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                module=_import_text(node, content),
                function=_function_name(func_node, content),
                language=language,
            ))
        return  # import nodes cannot contain further imports

    for child in node.children:  # type: ignore[attr-defined]
        _walk(child, content, file, language, import_types, function_types, out)


def _enclosing_function(node: object, function_types: frozenset[str]) -> object | None:
    """Walk parent chain; return first function-type ancestor or None."""
    parent = node.parent  # type: ignore[attr-defined]
    while parent is not None:
        if parent.type in function_types:  # type: ignore[attr-defined]
            return parent
        parent = parent.parent  # type: ignore[attr-defined]
    return None


def _function_name(node: object, content: bytes) -> str:
    """Best-effort function name from a function AST node."""
    name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
    for child in node.children:  # type: ignore[attr-defined]
        if child.type == "identifier":
            return content[child.start_byte:child.end_byte].decode(errors="replace")
    return "<anonymous>"


def _import_text(node: object, content: bytes) -> str:
    """First line of the import node, trimmed."""
    raw = content[node.start_byte:node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
    return raw.splitlines()[0].strip()


# ---------------------------------------------------------------------------
# Text tier (Rust)
# ---------------------------------------------------------------------------

_RUST_USE = re.compile(r'^(\s+)use\s+([\w:*{}\s,]+)')
_RUST_FN  = re.compile(r'^\s*(?:pub\s+(?:unsafe\s+|async\s+)?fn|fn)\s+(\w+)')


def _scan_rust_text(fp: Path) -> list[LocalImport]:
    """Indentation heuristic: a `use` with leading whitespace is inside a block."""
    try:
        lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    results: list[LocalImport] = []
    current_fn = "<anonymous>"
    for i, line in enumerate(lines, start=1):
        m_fn = _RUST_FN.match(line)
        if m_fn:
            current_fn = m_fn.group(1)
        m_use = _RUST_USE.match(line)
        if m_use:
            results.append(LocalImport(
                file=str(fp),
                line=i,
                module=m_use.group(2).strip(),
                function=current_fn,
                language="rust",
            ))
    return results
