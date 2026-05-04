"""God-module detection kernel.

Counts top-level callable definitions (functions and classes) per file.
A file with an excessively large number of top-level definitions is a
"god module" — it violates the Single Responsibility Principle and makes
navigation, testing, and ownership attribution harder.

"Top-level" means the definition is a direct child of the file's root node
(not nested inside another function or class).  Methods inside a class
count toward the class, not as extra top-level entries.

AST tier  — Python, JavaScript, TypeScript, Go, Rust, Java, C#, Julia.
Text tier — not needed; all supported languages have tree-sitter grammars.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Per-language top-level callable node types
# ---------------------------------------------------------------------------

#: Nodes that count as top-level callables (functions + class/struct definitions).
_TOP_LEVEL_NODES: dict[str, frozenset[str]] = {
    "python": frozenset({
        "function_definition",
        "decorated_definition",   # @decorator + def/class
        "class_definition",
    }),
    "javascript": frozenset({
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "lexical_declaration",     # const f = () => ...
        "variable_declaration",    # var/let f = function ...
    }),
    "typescript": frozenset({
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "lexical_declaration",
        "variable_declaration",
        "abstract_class_declaration",
    }),
    "go": frozenset({
        "function_declaration",
        "method_declaration",
        "type_declaration",       # type Foo struct / type Bar interface
    }),
    "rust": frozenset({
        "function_item",
        "impl_item",
        "struct_item",
        "trait_item",
        "enum_item",
    }),
    "java": frozenset({
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "method_declaration",
    }),
    "c_sharp": frozenset({
        "class_declaration",
        "interface_declaration",
        "struct_declaration",
        "method_declaration",
        "enum_declaration",
    }),
    "julia": frozenset({
        "function_definition",
        "struct_definition",
        "abstract_type_definition",
    }),
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
class GodModuleEntry:
    """One file that exceeded the top-level definition threshold."""

    file: str           # relative path
    language: str
    definition_count: int
    loc: int            # lines of code in the file


@dataclass
class GodModuleResult:
    """Aggregated result from god_module_kernel."""

    entries: list[GodModuleEntry] = field(default_factory=list)
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def god_module_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
) -> GodModuleResult:
    """Count top-level callable definitions per file.

    Args:
        root:      Search root.
        languages: Restrict to these languages (default: all supported).
        globs:     Include glob patterns.
        excludes:  Exclude patterns.
        hidden:    Search hidden files.
        no_ignore: Ignore .gitignore rules.
    """
    active = (
        {l.lower() for l in languages} & set(_TOP_LEVEL_NODES)
        if languages else set(_TOP_LEVEL_NODES)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])
    ]
    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    entries: list[GodModuleEntry] = []
    errors: list[str] = []

    for fp in files:
        lang = detect_language(fp)
        if lang not in active or lang not in _TOP_LEVEL_NODES:
            continue
        top_nodes = _TOP_LEVEL_NODES[lang]
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

            count = sum(
                1 for child in tree.root_node.children
                if child.type in top_nodes
            )
            loc = content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)
            rel = str(fp.relative_to(root))
            entries.append(GodModuleEntry(
                file=rel, language=lang, definition_count=count, loc=loc,
            ))
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    entries.sort(key=lambda e: -e.definition_count)
    return GodModuleResult(
        entries=entries,
        files_searched=len(files),
        errors=errors,
    )
