"""Shared function-definition enumeration + identifier tokenisation.

Several rules need the same primitives:

- "walk the AST of every file in scope, yield each function
  definition with enough context to do per-function analysis"
- "split an identifier into word tokens"

Without sharing, each rule re-implements the file-discovery + tree-
sitter loading + node-walking boilerplate, and each rule duplicates
identifier tokenisation.

This module provides:

- ``enumerate_functions`` — the canonical function-definition walker
- ``split_identifier`` — snake_case + CamelCase + acronym tokeniser

Callers iterate ``FunctionContext`` records and do per-rule work.
File discovery uses ``_fs.find_kernel``; AST loading uses
``_ast.treesitter``.

Per-language ``function_definition`` node types are listed in
``_FUNCTION_NODES``. The canonical sources for grammar node names
are the per-kernel ``_LangConfig`` dataclasses in ``_structural/``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel


# ---------------------------------------------------------------------------
# Identifier tokenisation
# ---------------------------------------------------------------------------

_CAMEL_LOWER_UPPER = re.compile(r"([a-z])([A-Z])")
_CAMEL_UPPER_TITLE = re.compile(r"([A-Z]+)([A-Z][a-z])")


def split_identifier(name: str) -> list[str]:
    """Split a snake_case or CamelCase identifier into word tokens.

    Examples::

        split_identifier("my_func")       -> ["my", "func"]
        split_identifier("processData")   -> ["process", "Data"]
        split_identifier("HTTPClient")    -> ["HTTP", "Client"]
        split_identifier("__init__")      -> ["init"]
        split_identifier("x")             -> ["x"]
    """
    name = name.strip("_")
    name = _CAMEL_LOWER_UPPER.sub(r"\1_\2", name)
    name = _CAMEL_UPPER_TITLE.sub(r"\1_\2", name)
    return [p for p in re.split(r"[_\d]+", name) if p]


def scope_label(parts: tuple[str, ...]) -> tuple[str, str]:
    """Render a path-parts tuple to ``(scope_str, scope_kind)``.

    ``parts`` is a tuple of path components (e.g. ``("cli", "slop",
    "output.py")``). Returns the joined-path string plus a kind label
    used by rules that report findings at hierarchical scope:

        ()                          -> ("<root>", "root")
        ("cli", "slop")             -> ("cli/slop", "package")
        ("cli", "slop", "output.py")-> ("cli/slop/output.py", "file")

    The "file" check is heuristic — last component contains a dot.
    Sufficient for the kinds of paths slop's rules walk.
    """
    if not parts:
        return ("<root>", "root")
    last = parts[-1]
    is_file = "." in last
    return ("/".join(parts), "file" if is_file else "package")


# ---------------------------------------------------------------------------
# Per-language function-node node types
# ---------------------------------------------------------------------------


_FUNCTION_NODES: dict[str, frozenset[str]] = {
    "python":     frozenset({"function_definition", "async_function_definition"}),
    "javascript": frozenset({"function_declaration", "function_expression",
                              "arrow_function", "method_definition",
                              "generator_function_declaration"}),
    "typescript": frozenset({"function_declaration", "function_expression",
                              "arrow_function", "method_definition",
                              "generator_function_declaration"}),
    "go":         frozenset({"function_declaration", "method_declaration",
                              "func_literal"}),
    "rust":       frozenset({"function_item"}),
    "java":       frozenset({"method_declaration", "constructor_declaration"}),
    "c_sharp":    frozenset({"method_declaration", "constructor_declaration",
                              "local_function_statement"}),
    "julia":      frozenset({"function_definition",
                              "arrow_function_expression"}),
    "c":          frozenset({"function_definition"}),
    "cpp":        frozenset({"function_definition", "lambda_expression"}),
    "ruby":       frozenset({"method", "singleton_method"}),
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
    "ruby":       ["**/*.rb"],
}


# ---------------------------------------------------------------------------
# Context dataclass
# ---------------------------------------------------------------------------


@dataclass
class FunctionContext:
    """One function-definition occurrence with enough context for per-rule work.

    Callers mostly want ``name`` and ``language``; rules that walk the
    body access ``node`` and ``content``; rules that inspect parameters
    or docstrings have language-specific extraction helpers (see
    ``slop._structural.composition`` for first-parameter and
    ``slop._lexical.boilerplate_docstrings`` for docstring extraction).
    """

    name: str                 # extracted function name, or "<lambda>" / "<anonymous>"
    file: str                 # relative path
    line: int                 # 1-based start line
    language: str             # detected language id
    node: Any                 # tree-sitter function-definition node
    body_node: Any | None     # body sub-node, or None if no body field
    content: bytes            # full file content (for substring extraction)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def enumerate_functions(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
) -> Iterator[FunctionContext]:
    """Yield every function-definition occurrence in the configured scope.

    Mirrors the shape of the existing kernel entry points
    (``ccx_kernel``, ``identifier_token_kernel``, etc.): the same
    ``languages`` / ``globs`` / ``excludes`` parameters; the same
    ``_fs.find_kernel`` + ``_ast.treesitter`` pattern.

    Yields each function in arbitrary order. Files that fail to parse
    are skipped silently (matches existing kernel behaviour; rules
    that need error visibility can wrap and inspect).
    """
    active = (
        {l.lower() for l in languages} & set(_FUNCTION_NODES)
        if languages else set(_FUNCTION_NODES)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])
    ]

    find_result = find_kernel(
        root=root, globs=find_globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    )
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    for fp in files:
        lang = detect_language(fp)
        if lang not in active or lang not in _FUNCTION_NODES:
            continue
        fn_node_types = _FUNCTION_NODES[lang]
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
        except Exception:
            continue

        try:
            rel = str(fp.relative_to(root))
        except ValueError:
            rel = str(fp)

        # DFS walk yielding every matching function-definition node.
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            ntype = node.type
            if ntype in fn_node_types:
                yield FunctionContext(
                    name=_extract_name(node, content, lang),
                    file=rel,
                    line=node.start_point[0] + 1,
                    language=lang,
                    node=node,
                    body_node=_extract_body(node, lang),
                    content=content,
                )
            stack.extend(reversed(node.children))


# ---------------------------------------------------------------------------
# Per-language name extraction
# ---------------------------------------------------------------------------


def _extract_name(node, content: bytes, language: str) -> str:
    """Extract function name. Falls back through name-field, language-
    specific declarator chains, and finally to ``"<anonymous>"``.
    """
    # Try the conventional ``name`` field first
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode(
            "utf-8", errors="replace",
        )

    # Anonymous function shapes
    if node.type in (
        "lambda", "arrow_function", "arrow_function_expression",
        "do_clause", "do_block", "block", "lambda_expression",
        "function_expression", "func_literal",
    ):
        return "<lambda>"

    # C / C++ declarator-chain
    if language in ("c", "cpp") and node.type == "function_definition":
        return _extract_c_or_cpp_name(node, content, language)

    # Ruby positional def name
    if language == "ruby" and node.type in ("method", "singleton_method"):
        return _extract_ruby_name(node, content)

    return "<anonymous>"


def _extract_c_or_cpp_name(node, content: bytes, language: str) -> str:
    """Walk the declarator chain — handles plain functions, pointer
    return, reference return, in-class methods (C++), out-of-line
    methods (C++), operator overloads (C++), destructors (C++)."""
    declarator = node.child_by_field_name("declarator")
    for _ in range(8):
        if declarator is None:
            return "<anonymous>"
        if declarator.type == "function_declarator":
            inner = declarator.child_by_field_name("declarator")
            if inner is None:
                return "<anonymous>"
            if inner.type in ("identifier", "field_identifier"):
                return content[inner.start_byte:inner.end_byte].decode(
                    "utf-8", errors="replace",
                )
            if language == "cpp":
                if inner.type == "qualified_identifier":
                    for c in reversed(inner.children):
                        if c.type == "identifier":
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
                if inner.type == "operator_name":
                    for c in inner.children:
                        if c.type != "operator":
                            return content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            ).strip()
                    return "<anonymous>"
                if inner.type == "destructor_name":
                    for c in inner.children:
                        if c.type == "identifier":
                            return "~" + content[c.start_byte:c.end_byte].decode(
                                "utf-8", errors="replace",
                            )
                    return "<anonymous>"
            return "<anonymous>"
        if declarator.type in (
            "pointer_declarator", "reference_declarator",
            "parenthesized_declarator",
        ):
            declarator = declarator.child_by_field_name("declarator")
            continue
        break
    return "<anonymous>"


def _extract_ruby_name(node, content: bytes) -> str:
    """Walk method / singleton_method children: skip ``def``,
    ``self``, ``.`` to find the ``identifier`` or ``operator``."""
    saw_def = False
    saw_self = False
    saw_dot = False
    for child in node.children:
        ctype = child.type
        if ctype == "def":
            saw_def = True
            continue
        if not saw_def:
            continue
        if ctype == "self" and not saw_self:
            saw_self = True
            continue
        if ctype == "." and saw_self and not saw_dot:
            saw_dot = True
            continue
        if ctype in ("identifier", "operator"):
            return content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            ).strip()
    return "<anonymous>"


# ---------------------------------------------------------------------------
# Body extraction
# ---------------------------------------------------------------------------


def _extract_body(node, language: str):
    """Best-effort body node extraction. Returns ``None`` if no body
    is exposed (rare; signals the caller to fall back to walking
    ``node`` directly)."""
    body = node.child_by_field_name("body")
    if body is not None:
        return body
    # Ruby uses a positional body_statement child
    if language == "ruby":
        for child in node.children:
            if child.type == "body_statement":
                return child
    return None
