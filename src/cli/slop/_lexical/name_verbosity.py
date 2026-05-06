"""Name verbosity kernel — flag function/class names exceeding N tokens.

A long *function name* is usually a class-without-class:
``check_required_binaries`` is three tokens because the namespace it
should belong to doesn't exist yet. Independent from
``lexical.verbosity`` (which measures *body* identifier verbosity).

See ``docs/backlog/01.md`` item 3 for the design.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel
from slop._lexical._naming import enumerate_functions
from slop._lexical.identifier_tokens import split_identifier


@dataclass
class VerboseName:
    name: str
    file: str
    line: int
    language: str
    kind: str          # "function" or "class"
    token_count: int
    tokens: list[str]


@dataclass
class NameVerbosityResult:
    items: list[VerboseName] = field(default_factory=list)
    files_searched: int = 0
    items_analyzed: int = 0
    errors: list[str] = field(default_factory=list)


# Per-language class-definition node types. Class names tokenised the
# same way; same threshold applies.
_CLASS_NODES: dict[str, frozenset[str]] = {
    "python":     frozenset({"class_definition"}),
    "javascript": frozenset({"class_declaration"}),
    "typescript": frozenset({"class_declaration", "interface_declaration"}),
    "java":       frozenset({"class_declaration", "interface_declaration"}),
    "c_sharp":    frozenset({"class_declaration", "interface_declaration"}),
    "cpp":        frozenset({"class_specifier", "struct_specifier"}),
    "ruby":       frozenset({"class", "module"}),
    "rust":       frozenset({"struct_item", "trait_item", "enum_item"}),
    "go":         frozenset({"type_declaration"}),
}

_LANG_GLOBS: dict[str, list[str]] = {
    "python":     ["**/*.py"],
    "javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],
    "typescript": ["**/*.ts", "**/*.tsx"],
    "go":         ["**/*.go"],
    "rust":       ["**/*.rs"],
    "java":       ["**/*.java"],
    "c_sharp":    ["**/*.cs"],
    "cpp":        ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],
    "ruby":       ["**/*.rb"],
}


def name_verbosity_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_tokens: int = 3,
    check_classes: bool = True,
) -> NameVerbosityResult:
    """Walk every function and class definition; flag names with > max_tokens
    word-tokens after snake/Camel split."""
    items: list[VerboseName] = []
    errors: list[str] = []

    # Functions via shared enumerator
    fn_count = 0
    files_set: set[str] = set()
    for ctx in enumerate_functions(
        root,
        languages=languages, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    ):
        fn_count += 1
        files_set.add(ctx.file)
        if ctx.name.startswith("<"):
            continue
        toks = [t for t in split_identifier(ctx.name) if t]
        if len(toks) > max_tokens:
            items.append(VerboseName(
                name=ctx.name, file=ctx.file, line=ctx.line,
                language=ctx.language, kind="function",
                token_count=len(toks), tokens=toks,
            ))

    if check_classes:
        # Class scan — independent walk because shared enumerator only
        # yields functions.
        active = (
            {l.lower() for l in languages} & set(_CLASS_NODES)
            if languages else set(_CLASS_NODES)
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
            if lang not in active or lang not in _CLASS_NODES:
                continue
            class_node_types = _CLASS_NODES[lang]
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
            except Exception as exc:
                errors.append(f"{fp}: {exc}")
                continue

            try:
                rel = str(fp.relative_to(root))
            except ValueError:
                rel = str(fp)
            files_set.add(rel)

            stack = [tree.root_node]
            while stack:
                node = stack.pop()
                if node.type in class_node_types:
                    name = _extract_type_name(node, content)
                    if name and not name.startswith("<"):
                        toks = [t for t in split_identifier(name) if t]
                        if len(toks) > max_tokens:
                            items.append(VerboseName(
                                name=name, file=rel,
                                line=node.start_point[0] + 1,
                                language=lang, kind="class",
                                token_count=len(toks), tokens=toks,
                            ))
                stack.extend(reversed(node.children))

    return NameVerbosityResult(
        items=items,
        files_searched=len(files_set),
        items_analyzed=fn_count + len(items),
        errors=errors,
    )


def _extract_type_name(node, content: bytes) -> str:
    """Best-effort name extraction for class/struct/interface/trait nodes."""
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode(
            "utf-8", errors="replace",
        )
    # Go: type_declaration -> type_spec -> name
    for child in node.children:
        if child.type == "type_spec":
            for grand in child.children:
                if grand.type == "type_identifier":
                    return content[grand.start_byte:grand.end_byte].decode(
                        "utf-8", errors="replace",
                    )
        if child.type in ("type_identifier", "identifier", "constant"):
            return content[child.start_byte:child.end_byte].decode(
                "utf-8", errors="replace",
            )
    return ""
