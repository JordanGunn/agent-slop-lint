"""Magic literal density kernel.

A *magic literal* is a numeric constant embedded directly in a function body
that has no symbolic name — the reader must infer its meaning from context.
Examples: ``timeout = 86400``, ``rate *= 1.047``, ``if code == 403:``.

The trivial constants 0, 1, and -1 are excluded from counting because they
appear frequently as loop bounds, sentinels, and increment values and rarely
require explanation.

Detection strategy
------------------
AST tier (tree-sitter): walk each function body and collect numeric-literal
nodes.  Literals whose numeric value is in the trivial-set are excluded.
The metric is the count of *distinct* non-trivial literal values per function.

Supported languages: Python, JavaScript, TypeScript, Go, Rust, Java, C#, Julia.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Trivial constants (excluded from counting)
# ---------------------------------------------------------------------------

_TRIVIAL_INTS: frozenset[int] = frozenset({0, 1, -1, 2})
# 2 is borderline but appears so often (doubling, binary) that false positives
# exceed signal; users may override by removing it from the allow-list.

_TRIVIAL_FLOATS: frozenset[float] = frozenset({0.0, 1.0, -1.0, 0.5, 2.0, 100.0})

# ---------------------------------------------------------------------------
# Per-language numeric literal node types
# ---------------------------------------------------------------------------

_NUMERIC_NODES: dict[str, frozenset[str]] = {
    "python":     frozenset({"integer", "float"}),
    "javascript": frozenset({"number"}),
    "typescript": frozenset({"number"}),
    "go":         frozenset({"int_literal", "float_literal",
                              "imaginary_literal", "rune_literal"}),
    "rust":       frozenset({"integer_literal", "float_literal"}),
    "java":       frozenset({"decimal_integer_literal", "decimal_floating_point_literal",
                              "hex_integer_literal", "octal_integer_literal"}),
    "c_sharp":    frozenset({"integer_literal", "real_literal"}),
    "julia":      frozenset({"integer_literal", "float_literal"}),
    "c":          frozenset({"number_literal"}),
    "cpp":        frozenset({"number_literal"}),
}

_FUNCTION_NODES: dict[str, frozenset[str]] = {
    "python":     frozenset({"function_definition", "async_function_definition"}),
    "javascript": frozenset({"function_declaration", "function_expression",
                              "arrow_function", "method_definition",
                              "generator_function_declaration"}),
    "typescript": frozenset({"function_declaration", "function_expression",
                              "arrow_function", "method_definition",
                              "generator_function_declaration"}),
    "go":         frozenset({"function_declaration", "method_declaration"}),
    "rust":       frozenset({"function_item"}),
    "java":       frozenset({"method_declaration", "constructor_declaration"}),
    "c_sharp":    frozenset({"method_declaration", "constructor_declaration",
                              "local_function_statement"}),
    "julia":      frozenset({"function_definition", "short_function_definition"}),
    "c":          frozenset({"function_definition"}),
    "cpp":        frozenset({"function_definition", "lambda_expression"}),
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
    "c":          ["**/*.c", "**/*.h"],
    "cpp":        ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class MagicLiteralEntry:
    """One function with too many distinct magic numeric literals."""

    file: str
    name: str
    line: int
    end_line: int
    language: str
    literals: list[str]         # raw text of non-trivial literals found
    distinct_count: int         # len(set(literals))


@dataclass
class MagicLiteralResult:
    """Aggregated result from magic_literals_kernel."""

    entries: list[MagicLiteralEntry] = field(default_factory=list)
    functions_analyzed: int = 0
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_trivial(text: str) -> bool:
    """Return True if the literal value is in the trivial-constant set."""
    # Strip language-specific suffixes (e.g. Rust's 1u32, 3.14f64)
    clean = re.sub(r'[_a-zA-Z]+$', '', text).replace("_", "")
    try:
        val = int(clean, 0)
        return val in _TRIVIAL_INTS
    except ValueError:
        pass
    try:
        val_f = float(clean)
        return val_f in _TRIVIAL_FLOATS
    except ValueError:
        pass
    return False


def _fn_name(node: object, content: bytes) -> str:
    name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
    # C / C++ ``function_definition`` exposes the name through the
    # declarator chain rather than a ``name`` field. Walk it through
    # pointer / reference / parenthesized declarator wrappers to the
    # inner ``function_declarator``, then take its ``declarator`` field
    # which is one of: identifier (plain C), field_identifier (C++
    # in-class method), qualified_identifier (C++ out-of-line method —
    # rightmost identifier), operator_name (C++ operator overload —
    # the operator-symbol child), or destructor_name (C++ destructor —
    # inner identifier, prefixed with ~).
    if node.type in ("function_definition", "lambda_expression"):  # type: ignore[attr-defined]
        if node.type == "lambda_expression":  # type: ignore[attr-defined]
            return "<lambda>"
        declarator = node.child_by_field_name("declarator")  # type: ignore[attr-defined]
        for _ in range(8):
            if declarator is None:
                break
            if declarator.type == "function_declarator":  # type: ignore[attr-defined]
                inner = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
                if inner is None:
                    break
                if inner.type in ("identifier", "field_identifier"):  # type: ignore[attr-defined]
                    return content[inner.start_byte:inner.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if inner.type == "qualified_identifier":  # type: ignore[attr-defined]
                    for c in reversed(inner.children):  # type: ignore[attr-defined]
                        if c.type == "identifier":  # type: ignore[attr-defined]
                            return content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    break
                if inner.type == "operator_name":  # type: ignore[attr-defined]
                    for c in inner.children:  # type: ignore[attr-defined]
                        if c.type != "operator":  # type: ignore[attr-defined]
                            return content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    break
                if inner.type == "destructor_name":  # type: ignore[attr-defined]
                    for c in inner.children:  # type: ignore[attr-defined]
                        if c.type == "identifier":  # type: ignore[attr-defined]
                            return "~" + content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    break
                break
            if declarator.type in ("pointer_declarator", "reference_declarator", "parenthesized_declarator"):  # type: ignore[attr-defined]
                declarator = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
                continue
            break
    for child in node.children:  # type: ignore[attr-defined]
        if child.type == "identifier":
            return content[child.start_byte:child.end_byte].decode(errors="replace")
    return "<anonymous>"



# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def magic_literals_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
) -> MagicLiteralResult:
    """Count distinct non-trivial numeric literals per function body.

    Args:
        root:      Search root.
        languages: Restrict to these languages (default: all supported).
        globs:     Include glob patterns.
        excludes:  Exclude patterns.
        hidden:    Search hidden files.
        no_ignore: Ignore .gitignore rules.
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

    entries: list[MagicLiteralEntry] = []
    errors: list[str] = []
    total_functions = 0

    for fp in files:
        lang = detect_language(fp)
        if lang not in active:
            continue
        fn_nodes = _FUNCTION_NODES.get(lang)
        numeric_nodes = _NUMERIC_NODES.get(lang)
        if fn_nodes is None or numeric_nodes is None:
            continue
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
            stack = [tree.root_node]
            while stack:
                node = stack.pop()
                if node.type in fn_nodes:  # type: ignore[attr-defined]
                    total_functions += 1
                    body = node.child_by_field_name("body") or node  # type: ignore[attr-defined]
                    literals = _collect_numeric_literals(body, content, numeric_nodes)
                    if literals:
                        distinct = sorted(set(literals))
                        entries.append(MagicLiteralEntry(
                            file=rel,
                            name=_fn_name(node, content),
                            line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                            end_line=node.end_point[0] + 1,  # type: ignore[attr-defined]
                            language=lang,
                            literals=literals,
                            distinct_count=len(distinct),
                        ))
                stack.extend(node.children)  # type: ignore[attr-defined]
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    entries.sort(key=lambda e: -e.distinct_count)
    return MagicLiteralResult(
        entries=entries,
        functions_analyzed=total_functions,
        files_searched=len(files),
        errors=errors,
    )


def _collect_numeric_literals(node: object, content: bytes, numeric_types: frozenset) -> list[str]:
    """DFS collect all non-trivial numeric literal texts in a subtree."""
    result: list[str] = []
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in numeric_types:  # type: ignore[attr-defined]
            text = content[n.start_byte:n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if not _is_trivial(text):
                result.append(text)
        else:
            stack.extend(n.children)  # type: ignore[attr-defined]
    return result
