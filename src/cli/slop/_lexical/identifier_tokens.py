"""Identifier token count kernel.

Tokenises every identifier inside a function body by splitting on
snake_case underscores and CamelCase transitions.  The resulting
*mean tokens-per-identifier* is a naming-verbosity signal:

  1.0 → every identifier is a single letter or single word  (terse)
  3.5 → identifiers carry multi-word context on average     (verbose)

Reused by:
  lexical.verbosity – flags functions with over-verbose multi-token names
  lexical.tersity   – fraction of ≤2-char identifiers (guardrail)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Identifier splitting
# ---------------------------------------------------------------------------

_CAMEL_LOWER_UPPER = re.compile(r'([a-z])([A-Z])')
_CAMEL_UPPER_TITLE = re.compile(r'([A-Z]+)([A-Z][a-z])')


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
    name = _CAMEL_LOWER_UPPER.sub(r'\1_\2', name)
    name = _CAMEL_UPPER_TITLE.sub(r'\1_\2', name)
    return [p for p in re.split(r'[_\d]+', name) if p]


# ---------------------------------------------------------------------------
# Per-language tables
# ---------------------------------------------------------------------------

#: Function / method boundary node types per language.
_FUNCTION_NODES: dict[str, frozenset[str]] = {
    "python":     frozenset({"function_definition"}),
    "javascript": frozenset({"function_declaration", "function", "arrow_function",
                              "method_definition", "generator_function_declaration"}),
    "typescript": frozenset({"function_declaration", "function", "arrow_function",
                              "method_definition", "generator_function_declaration"}),
    "go":         frozenset({"function_declaration", "method_declaration", "func_literal"}),
    "rust":       frozenset({"function_item"}),
    "java":       frozenset({"method_declaration", "constructor_declaration"}),
    "c_sharp":    frozenset({"method_declaration", "constructor_declaration"}),
    "julia":      frozenset({"function_definition", "arrow_function_expression"}),
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
class FunctionIdentifiers:
    """Identifier token statistics for one function."""

    name: str
    file: str           # relative path
    line: int           # 1-based start
    end_line: int
    language: str
    identifiers: list[str]      # raw identifier strings found in body
    token_counts: list[int]     # token count per identifier
    mean_tokens: float          # mean tokens-per-identifier (0.0 if no ids)
    total_identifiers: int
    total_tokens: int


@dataclass
class IdentifierTokenResult:
    """Aggregated result from identifier_token_kernel."""

    functions: list[FunctionIdentifiers] = field(default_factory=list)
    files_searched: int = 0
    functions_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def identifier_token_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
) -> IdentifierTokenResult:
    """Compute mean identifier token count per function across a codebase."""
    active = (
        {l.lower() for l in languages} & set(_FUNCTION_NODES)
        if languages else set(_FUNCTION_NODES)
    )
    find_globs = list(globs) if globs else [g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])]

    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    functions: list[FunctionIdentifiers] = []
    errors: list[str] = []

    for fp in files:
        lang = detect_language(fp)
        if lang not in active or lang not in _FUNCTION_NODES:
            continue
        lang_fn_nodes = _FUNCTION_NODES[lang]
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
                # Modern API: no-arg constructor + .language attribute
                parser = tree_sitter.Parser()
                parser.language = tree_lang  # type: ignore[assignment]
                tree = parser.parse(content)

            rel = str(fp.relative_to(root))
            _scan_file(tree.root_node, content, rel, lang, lang_fn_nodes, functions)
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    return IdentifierTokenResult(
        functions=functions,
        files_searched=len(files),
        functions_analyzed=len(functions),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scan_file(
    root_node: object,
    content: bytes,
    rel: str,
    lang: str,
    fn_nodes: frozenset[str],
    out: list[FunctionIdentifiers],
) -> None:
    """DFS walk; for each function node collect body identifiers."""
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type in fn_nodes:  # type: ignore[attr-defined]
            _process_function(node, content, rel, lang, out)
            # Don't descend — inner functions collected separately by the caller
            # re-pushing them; but we do want nested functions counted, so continue:
            stack.extend(reversed(node.children))  # type: ignore[attr-defined]
        else:
            stack.extend(reversed(node.children))  # type: ignore[attr-defined]


def _process_function(
    node: object,
    content: bytes,
    rel: str,
    lang: str,
    out: list[FunctionIdentifiers],
) -> None:
    """Compute identifier token stats for one function node."""
    name = _fn_name(node, content)
    body = node.child_by_field_name("body") or node  # type: ignore[attr-defined]

    identifiers: list[str] = []
    _collect_identifiers(body, content, identifiers)

    if not identifiers:
        return

    token_counts = [len(split_identifier(i)) or 1 for i in identifiers]
    total_tokens = sum(token_counts)
    mean = total_tokens / len(identifiers)

    out.append(FunctionIdentifiers(
        name=name,
        file=rel,
        line=node.start_point[0] + 1,  # type: ignore[attr-defined]
        end_line=node.end_point[0] + 1,  # type: ignore[attr-defined]
        language=lang,
        identifiers=identifiers,
        token_counts=token_counts,
        mean_tokens=round(mean, 3),
        total_identifiers=len(identifiers),
        total_tokens=total_tokens,
    ))


def _collect_identifiers(node: object, content: bytes, out: list[str]) -> None:
    """DFS collect all identifier leaf nodes inside a subtree."""
    if node.type == "identifier" and node.child_count == 0:  # type: ignore[attr-defined]
        text = content[node.start_byte:node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
        out.append(text)
    else:
        for child in node.children:  # type: ignore[attr-defined]
            _collect_identifiers(child, content, out)


def _fn_name(node: object, content: bytes) -> str:
    """Best-effort function name from a function AST node."""
    name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
    for child in node.children:  # type: ignore[attr-defined]
        if child.type == "identifier":
            return content[child.start_byte:child.end_byte].decode(errors="replace")
    return "<anonymous>"
