"""Section-comment density kernel.

A *section divider comment* is a comment whose text consists almost entirely
of punctuation characters used as visual separators — e.g.::

    # --- Phase 1 ---
    # =================
    # *** Setup ***

When a function body contains multiple such comments it is a signal that the
function has grown into several conceptually distinct phases and should be
split into smaller helpers.

Two-tier detection
------------------
1. **ripgrep tier**: find all divider-style comment lines in source files.
2. **AST tier**: for each match, confirm it falls inside a function/method body
   and attribute it to that function.

Languages: Python, JavaScript, TypeScript, Go, Rust, Java, C#, Julia.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._text.grep import grep_kernel
from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Comment divider pattern
# ---------------------------------------------------------------------------

#: Regex that matches a line containing a divider-style comment.
#: Accepts Python (#), JS/TS/Go/Rust/Java/C#/C99 (//), Julia (#), and
#: C block-style (/* === ... ===).
_DIVIDER_PATTERN = r"(?:#|//|/\*)\s*[-=*~+_#]{3,}"

# ---------------------------------------------------------------------------
# Per-language function node types (body span check)
# ---------------------------------------------------------------------------

_FUNCTION_NODES: dict[str, frozenset[str]] = {
    "python": frozenset({"function_definition", "async_function_definition"}),
    "javascript": frozenset({
        "function_declaration", "function_expression", "arrow_function",
        "method_definition", "generator_function_declaration",
    }),
    "typescript": frozenset({
        "function_declaration", "function_expression", "arrow_function",
        "method_definition", "generator_function_declaration",
    }),
    "go": frozenset({"function_declaration", "method_declaration"}),
    "rust": frozenset({"function_item"}),
    "java": frozenset({"method_declaration", "constructor_declaration"}),
    "c_sharp": frozenset({"method_declaration", "constructor_declaration",
                           "local_function_statement"}),
    "julia": frozenset({"function_definition", "short_function_definition"}),
    "c": frozenset({"function_definition"}),
    "cpp": frozenset({"function_definition", "lambda_expression"}),
    "ruby": frozenset({"method", "singleton_method", "lambda", "do_block", "block"}),
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
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SectionCommentEntry:
    """One function that exceeded the section-divider threshold."""

    file: str           # relative path
    name: str
    line: int           # 1-based function start
    end_line: int
    language: str
    divider_count: int
    divider_lines: list[int]  # 1-based line numbers of dividers inside this fn


@dataclass
class SectionCommentResult:
    """Aggregated result from section_comment_kernel."""

    entries: list[SectionCommentEntry] = field(default_factory=list)
    functions_analyzed: int = 0
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def section_comment_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
) -> SectionCommentResult:
    """Find functions that overuse section-divider comments."""
    active = (
        {l.lower() for l in languages} & set(_FUNCTION_NODES)
        if languages else set(_FUNCTION_NODES)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])
    ]

    # --- Tier 1: ripgrep pass ---
    grep_result = grep_kernel(
        patterns=[{"kind": "regex", "value": _DIVIDER_PATTERN}],
        root=root,
        globs=find_globs,
        excludes=excludes or [],
        hidden=hidden,
        no_ignore=no_ignore,
    )

    # Group grep hits by (relative) file path → set of line numbers
    hits_by_file: dict[str, set[int]] = defaultdict(set)
    for m in grep_result.matches:
        # m.path is relative to root (rg default without --no-relative)
        hits_by_file[m.path].add(m.line_number)

    if not hits_by_file:
        # No divider comments found — still count files
        find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                                  hidden=hidden, no_ignore=no_ignore)
        return SectionCommentResult(
            entries=[],
            functions_analyzed=0,
            files_searched=len(find_result.entries),
        )

    # --- Tier 2: AST confirmation pass ---
    entries: list[SectionCommentEntry] = []
    errors: list[str] = []
    total_functions = 0

    for rel_path, hit_lines in hits_by_file.items():
        fp = root / rel_path
        if not fp.exists():
            continue
        lang = detect_language(fp)
        if lang not in active or lang not in _FUNCTION_NODES:
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

            func_nodes = _FUNCTION_NODES[lang]
            for node in _iter_nodes(tree.root_node):
                if node.type not in func_nodes:  # type: ignore[attr-defined]
                    continue
                total_functions += 1
                fn_start = node.start_point[0] + 1  # type: ignore[attr-defined]
                fn_end = node.end_point[0] + 1      # type: ignore[attr-defined]
                inside = sorted(
                    ln for ln in hit_lines if fn_start <= ln <= fn_end
                )
                if inside:
                    fn_name = _fn_name(node, content)
                    entries.append(SectionCommentEntry(
                        file=rel_path,
                        name=fn_name,
                        line=fn_start,
                        end_line=fn_end,
                        language=lang,
                        divider_count=len(inside),
                        divider_lines=inside,
                    ))
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    # Files searched = those that had grep hits (only files with dividers matter)
    return SectionCommentResult(
        entries=entries,
        functions_analyzed=total_functions,
        files_searched=len(hits_by_file),
        errors=errors,
    )


def _iter_nodes(node: object):
    """DFS generator over AST nodes."""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)  # type: ignore[attr-defined]


def _fn_name(node: object, content: bytes) -> str:
    name_node = node.child_by_field_name("name")  # type: ignore[attr-defined]
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
    # C / C++ ``function_definition``: walk declarator chain. See
    # ``slop._structural.magic_literals._fn_name`` for the canonical
    # cases handled (plain, in-class field_identifier, out-of-line
    # qualified_identifier, operator_name, destructor_name).
    if node.type in ("lambda", "do_block", "block"):  # type: ignore[attr-defined]
        return "<lambda>"
    if node.type in ("method", "singleton_method"):  # type: ignore[attr-defined]
        saw_def = False
        saw_self = False
        saw_dot = False
        for child in node.children:  # type: ignore[attr-defined]
            ctype = child.type  # type: ignore[attr-defined]
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
                return content[child.start_byte:child.end_byte].decode(errors="replace").strip()  # type: ignore[attr-defined]
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
