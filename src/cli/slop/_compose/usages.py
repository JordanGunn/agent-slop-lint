"""Usages kernel - symbol cross-reference via grep + tree-sitter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._fs.find import find_kernel
from slop._text.grep import grep_kernel


# Definition queries per language: list of (query_string, symbol_type_label)
DEFINITION_QUERIES: dict[str, list[tuple[str, str]]] = {
    "python": [
        ("(function_definition name: (identifier) @name)", "function"),
        ("(class_definition name: (identifier) @name)", "class"),
    ],
    "javascript": [
        ("(function_declaration name: (identifier) @name)", "function"),
        ("(class_declaration name: (identifier) @name)", "class"),
    ],
    "typescript": [
        ("(function_declaration name: (identifier) @name)", "function"),
        ("(class_declaration name: (identifier) @name)", "class"),
        ("(interface_declaration name: (type_identifier) @name)", "interface"),
        ("(type_alias_declaration name: (type_identifier) @name)", "type"),
    ],
    "go": [
        ("(function_declaration name: (identifier) @name)", "function"),
        ("(type_declaration (type_spec name: (type_identifier) @name))", "type"),
    ],
    "rust": [
        ("(function_item name: (identifier) @name)", "function"),
        ("(struct_item name: (type_identifier) @name)", "struct"),
        ("(enum_item name: (type_identifier) @name)", "enum"),
    ],
    "java": [
        ("(method_declaration name: (identifier) @name)", "method"),
        ("(class_declaration name: (identifier) @name)", "class"),
        ("(interface_declaration name: (identifier) @name)", "interface"),
    ],
    "c_sharp": [
        ("(method_declaration name: (identifier) @name)", "method"),
        ("(class_declaration name: (identifier) @name)", "class"),
        ("(struct_declaration name: (identifier) @name)", "struct"),
        ("(interface_declaration name: (identifier) @name)", "interface"),
        ("(constructor_declaration name: (identifier) @name)", "constructor"),
        ("(property_declaration name: (identifier) @name)", "property"),
    ],
    "julia": [
        # function f(...) ... end → captures the call_expression's identifier
        ("(function_definition (signature (call_expression (identifier) @name)))", "function"),
        # struct X / mutable struct X
        ("(struct_definition (type_head (identifier) @name))", "struct"),
        # abstract type X end
        ("(abstract_definition (type_head (identifier) @name))", "abstract"),
    ],
}


@dataclass
class UsagesEntry:
    """A single usage — definition or reference."""

    kind: str           # "definition" | "reference"
    file: str           # absolute path
    line: int           # 1-based
    content: str        # matched line text
    col: int = 0        # 0-based column (definition entries only, from AST)
    symbol_type: str | None = None  # "class", "function", etc. (definition only)


@dataclass
class UsagesResult:
    """Aggregated usages results."""

    symbol: str
    definitions: list[UsagesEntry]
    references: list[UsagesEntry]
    files_searched: int
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


def usages_kernel(
    root: Path,
    symbol: str,
    *,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    language: str | None = None,
    include_definitions: bool = True,
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
) -> UsagesResult:
    """Find all definitions and references of a symbol.

    Args:
        root: Search root directory
        symbol: Exact symbol name (literal string, not regex)
        globs: Include glob patterns
        excludes: Exclude glob patterns
        language: Tree-sitter language override for definition detection
        include_definitions: Attempt AST definition tagging (requires tree-sitter)
        hidden: Search hidden files
        no_ignore: Don't respect gitignore
        max_results: Maximum total matches to return

    Returns:
        UsagesResult with definitions and references separated
    """
    # Step 1: File discovery
    find_result = find_kernel(
        root=root,
        globs=globs,
        excludes=excludes,
        hidden=hidden,
        no_ignore=no_ignore,
    )

    file_paths = [root / e.path for e in find_result.entries if e.type == "file"]

    if not file_paths:
        return UsagesResult(
            symbol=symbol,
            definitions=[],
            references=[],
            files_searched=find_result.total_found,
            errors=find_result.errors,
        )

    # Step 2: Text search — fixed-string, case-sensitive
    grep_result = grep_kernel(
        patterns=[{"kind": "fixed", "value": symbol}],
        root=root,
        files=file_paths,
        mode="fixed",
        case="sensitive",
        max_matches=max_results,
    )

    errors: list[str] = list(find_result.errors) + list(grep_result.errors)

    # Step 3: AST definition extraction
    # Maps (abs_path_str, line) -> (symbol_type, col)
    definition_map: dict[tuple[str, int], tuple[str, int]] = {}

    if include_definitions and grep_result.matches:
        def_map, def_errors = _find_definitions(file_paths, symbol, language)
        definition_map = def_map
        errors.extend(def_errors)

    # Step 4: Correlate grep matches → kind classification
    definitions: list[UsagesEntry] = []
    references: list[UsagesEntry] = []

    for match in grep_result.matches:
        key = (match.path, match.line_number)
        if key in definition_map:
            symbol_type, col = definition_map[key]
            definitions.append(UsagesEntry(
                kind="definition",
                file=match.path,
                line=match.line_number,
                content=match.content,
                col=col,
                symbol_type=symbol_type,
            ))
        else:
            references.append(UsagesEntry(
                kind="reference",
                file=match.path,
                line=match.line_number,
                content=match.content,
            ))

    return UsagesResult(
        symbol=symbol,
        definitions=definitions,
        references=references,
        files_searched=find_result.total_found,
        errors=errors,
        truncated=grep_result.truncated,
    )


def _find_definitions(
    files: list[Path],
    symbol: str,
    language_override: str | None,
) -> tuple[dict[tuple[str, int], tuple[str, int]], list[str]]:
    """Run definition queries against candidate files.

    Returns:
        Tuple of (definition_map, errors) where definition_map maps
        (abs_path_str, line) -> (symbol_type, col).
    """
    from slop._ast.query import query_kernel
    from slop._ast.treesitter import detect_language

    definition_map: dict[tuple[str, int], tuple[str, int]] = {}
    errors: list[str] = []

    if language_override:
        # All files treated as the given language
        if language_override not in DEFINITION_QUERIES:
            return {}, []
        lang_files: dict[str, list[Path]] = {language_override: files}
    else:
        lang_files = {}
        for f in files:
            lang = detect_language(f)
            if lang and lang in DEFINITION_QUERIES:
                lang_files.setdefault(lang, []).append(f)

    for lang_name, lang_file_list in lang_files.items():
        for query_str, symbol_type in DEFINITION_QUERIES[lang_name]:
            result = query_kernel(
                files=lang_file_list,
                query_str=query_str,
                language=lang_name,
            )
            errors.extend(result.errors)
            for match in result.matches:
                for cap in match.captures:
                    if cap.name == "name" and cap.text == symbol:
                        key = (match.file, cap.line)
                        definition_map[key] = (symbol_type, cap.col)

    return definition_map, errors
