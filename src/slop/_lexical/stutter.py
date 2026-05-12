"""Stutter detection kernel — hierarchy-aware.

Detects names that repeat tokens from any enclosing scope. The
hierarchy is::

    package (parent directory) → module (file stem) → class → function

Two kinds of stutter are detected:

1. **Entity-name stutter.** A class/function/method NAME stutters
   with one of its enclosing scope names. Catches the case where
   the entity itself is named redundantly relative to where it
   lives. Example: ``class UserService`` containing
   ``def get_user_service_id(self): ...`` — the method name
   stutters with the class name.

2. **Identifier stutter.** A local identifier inside a function
   body stutters with one of its enclosing scope names.
   Example: ``def check_required_binaries():
   required_binaries = [...]`` — the local repeats the function
   name's tokens.

Each finding carries a ``level`` (``package`` | ``module`` |
``class`` | ``function``) indicating which scope kind triggered it.
Per-level toggle parameters in the rule wrapper let users dial
down specific levels (preserves the v1.1.0 split's per-level
configurability without splitting the rule).

Token comparison is case-insensitive (``UserService`` ↔
``user_service_helper`` matches correctly).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel
from slop._lexical._naming import split_identifier


# Per-language scope-defining node types.
_SCOPE_NODES: dict[str, dict[str, frozenset[str]]] = {
    "python": {
        "function": frozenset({"function_definition"}),
        "class": frozenset({"class_definition"}),
    },
    "javascript": {
        "function": frozenset({"function_declaration", "function", "arrow_function",
                               "method_definition", "generator_function_declaration"}),
        "class": frozenset({"class_declaration"}),
    },
    "typescript": {
        "function": frozenset({"function_declaration", "function", "arrow_function",
                               "method_definition", "generator_function_declaration"}),
        "class": frozenset({"class_declaration"}),
    },
    "go": {
        "function": frozenset({"function_declaration", "method_declaration", "func_literal"}),
        "class": frozenset({"type_declaration"}),
    },
    "rust": {
        "function": frozenset({"function_item"}),
        "class": frozenset({"struct_item", "enum_item", "impl_item"}),
    },
    "c": {
        "function": frozenset({"function_definition"}),
        "class": frozenset(),
    },
    "cpp": {
        "function": frozenset({"function_definition", "lambda_expression"}),
        "class": frozenset({
            "class_specifier", "struct_specifier", "namespace_definition",
        }),
    },
    "ruby": {
        "function": frozenset({"method", "singleton_method", "lambda", "do_block", "block"}),
        "class": frozenset({"class", "module"}),
    },
}

_LANG_GLOBS: dict[str, list[str]] = {
    "python":     ["**/*.py"],
    "javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],
    "typescript": ["**/*.ts", "**/*.tsx"],
    "go":         ["**/*.go"],
    "rust":       ["**/*.rs"],
    "c":          ["**/*.c", "**/*.h"],
    "cpp":        ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],
    "ruby":       ["**/*.rb"],
}


#: Valid scope-level names. Order matches enclosing-scope hierarchy
#: from outermost to innermost.
ALL_LEVELS: frozenset[str] = frozenset({"package", "module", "class", "function"})


@dataclass
class StutterViolation:
    """One stutter finding.

    Either an entity-name stutter (the entity's own name stutters
    with an enclosing scope) or an identifier stutter (a body
    identifier inside a function stutters with an enclosing scope).
    """
    identifier: str
    tokens: list[str]
    file: str
    line: int
    column: int
    language: str
    scope_name: str         # name of the enclosing scope this stutters with
    scope_level: str        # 'package' | 'module' | 'class' | 'function'
    overlap: list[str]
    is_entity_name: bool    # True: this IS a class/function/method name;
                            # False: this is a body identifier


@dataclass
class StutterResult:
    violations: list[StutterViolation] = field(default_factory=list)
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


def _lowercase_tokens(name: str) -> set[str]:
    return {t.lower() for t in split_identifier(name)}


def stutter_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    excludes: list[str] | None = None,
    levels: frozenset[str] = ALL_LEVELS,
) -> StutterResult:
    """Run hierarchy-aware stutter detection.

    ``levels`` selects which enclosing-scope kinds to check. Default
    is all four (package / module / class / function).
    """
    active = ({l.lower() for l in languages} & set(_SCOPE_NODES)) if languages else set(_SCOPE_NODES)
    find_globs = [g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])]

    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    violations: list[StutterViolation] = []
    errors: list[str] = []

    for fp in files:
        lang = detect_language(fp)
        if lang not in active:
            continue

        tree_lang = load_language(lang)
        if tree_lang is None:
            continue

        try:
            import tree_sitter
            content = fp.read_bytes()
            parser = tree_sitter.Parser()
            parser.language = tree_lang  # type: ignore[assignment]
            tree = parser.parse(content)

            rel = str(fp.relative_to(root))
            # Initial scope stack: package (parent dir) + module (file stem).
            initial_stack: list[tuple[str, str, set[str]]] = []
            try:
                parent_dir = fp.parent.name
                if parent_dir:
                    initial_stack.append(
                        (parent_dir, "package", _lowercase_tokens(parent_dir)),
                    )
            except Exception:
                pass
            module_name = fp.stem
            initial_stack.append(
                (module_name, "module", _lowercase_tokens(module_name)),
            )

            _scan_file(
                tree.root_node, content, rel, lang, initial_stack,
                violations, levels,
            )
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    return StutterResult(
        violations=violations,
        files_searched=len(files),
        errors=errors,
    )


def _check_against_scopes(
    name: str,
    tokens_lower: set[str],
    scope_stack: list[tuple[str, str, set[str]]],
    levels: frozenset[str],
    is_entity_name: bool,
    file: str,
    line: int,
    column: int,
    language: str,
    out: list[StutterViolation],
) -> None:
    """Compare an identifier (or entity name) against each scope on
    the stack. Emit one violation for the most-immediate stutter
    (deepest scope wins; matches v1.1.0 behaviour)."""
    for scope_name, scope_level, scope_tokens in reversed(scope_stack):
        if scope_level not in levels:
            continue
        # Don't compare an entity to itself: when checking a
        # function's name against the scope_stack, the function's
        # own scope frame might be on the stack (it shouldn't, by
        # construction — caller passes the parent stack — but
        # defensive).
        if is_entity_name and scope_name == name:
            continue
        overlap = tokens_lower & scope_tokens
        if len(overlap) >= 2:
            out.append(StutterViolation(
                identifier=name,
                tokens=sorted(tokens_lower),
                file=file,
                line=line,
                column=column,
                language=language,
                scope_name=scope_name,
                scope_level=scope_level,
                overlap=sorted(overlap),
                is_entity_name=is_entity_name,
            ))
            return  # most-immediate match wins


def _scan_file(
    root_node, content, rel, lang,
    initial_stack: list[tuple[str, str, set[str]]],
    violations: list[StutterViolation],
    levels: frozenset[str],
) -> None:
    fn_nodes = _SCOPE_NODES[lang]["function"]
    class_nodes = _SCOPE_NODES[lang]["class"]

    # DFS via explicit stack: each entry is (node, scope_stack_for_this_node).
    stack: list[tuple[object, list[tuple[str, str, set[str]]]]] = [
        (root_node, initial_stack),
    ]

    while stack:
        node, scope_stack = stack.pop()
        next_scope_stack = scope_stack

        if node.type in fn_nodes:  # type: ignore[attr-defined]
            name = _get_name(node, content)
            if name and not name.startswith("<"):
                # Check the function/method NAME against enclosing
                # scopes (entity-name stutter).
                _check_against_scopes(
                    name=name,
                    tokens_lower=_lowercase_tokens(name),
                    scope_stack=scope_stack,
                    levels=levels,
                    is_entity_name=True,
                    file=rel,
                    line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                    column=node.start_point[1],  # type: ignore[attr-defined]
                    language=lang,
                    out=violations,
                )
                next_scope_stack = scope_stack + [
                    (name, "function", _lowercase_tokens(name)),
                ]
            # Check identifiers within the function body against
            # all enclosing scopes (including function itself).
            _process_function_body(
                node, content, rel, lang, next_scope_stack,
                levels, violations,
            )

        elif node.type in class_nodes:  # type: ignore[attr-defined]
            name = _get_name(node, content)
            if name and not name.startswith("<"):
                # Check the class NAME against enclosing scopes
                # (entity-name stutter).
                _check_against_scopes(
                    name=name,
                    tokens_lower=_lowercase_tokens(name),
                    scope_stack=scope_stack,
                    levels=levels,
                    is_entity_name=True,
                    file=rel,
                    line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                    column=node.start_point[1],  # type: ignore[attr-defined]
                    language=lang,
                    out=violations,
                )
                next_scope_stack = scope_stack + [
                    (name, "class", _lowercase_tokens(name)),
                ]

        for child in reversed(node.children):  # type: ignore[attr-defined]
            stack.append((child, next_scope_stack))


def _process_function_body(
    fn_node, content, rel: str, lang: str,
    scope_stack: list[tuple[str, str, set[str]]],
    levels: frozenset[str],
    violations: list[StutterViolation],
) -> None:
    body = fn_node.child_by_field_name("body") or fn_node
    identifiers: list = []
    _collect_identifier_nodes(body, identifiers)

    for ident_node in identifiers:
        name = content[ident_node.start_byte:ident_node.end_byte].decode(errors="replace")
        if name.startswith("_") and not name.startswith("__"):
            continue
        tokens = split_identifier(name)
        if not tokens:
            continue
        token_set = {t.lower() for t in tokens}
        _check_against_scopes(
            name=name,
            tokens_lower=token_set,
            scope_stack=scope_stack,
            levels=levels,
            is_entity_name=False,
            file=rel,
            line=ident_node.start_point[0] + 1,
            column=ident_node.start_point[1],
            language=lang,
            out=violations,
        )


def _collect_identifier_nodes(node, out):
    if node.type == "identifier" and node.child_count == 0:
        out.append(node)
    else:
        for child in node.children:
            _collect_identifier_nodes(child, out)


def _get_name(node, content) -> str:
    name_node = node.child_by_field_name("name")
    if name_node:
        return content[name_node.start_byte:name_node.end_byte].decode(errors="replace")
    if node.type in ("lambda", "do_block", "block"):
        return "<lambda>"
    if node.type in ("method", "singleton_method"):
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
                return content[child.start_byte:child.end_byte].decode(errors="replace").strip()
    if node.type in ("function_definition", "lambda_expression"):
        if node.type == "lambda_expression":
            return "<lambda>"
        declarator = node.child_by_field_name("declarator")
        for _ in range(8):
            if declarator is None:
                break
            if declarator.type == "function_declarator":
                inner = declarator.child_by_field_name("declarator")
                if inner is None:
                    break
                if inner.type in ("identifier", "field_identifier"):
                    return content[inner.start_byte:inner.end_byte].decode(errors="replace")
                if inner.type == "qualified_identifier":
                    for c in reversed(inner.children):
                        if c.type == "identifier":
                            return content[c.start_byte:c.end_byte].decode(errors="replace")
                    break
                if inner.type == "operator_name":
                    for c in inner.children:
                        if c.type != "operator":
                            return content[c.start_byte:c.end_byte].decode(errors="replace")
                    break
                if inner.type == "destructor_name":
                    for c in inner.children:
                        if c.type == "identifier":
                            return "~" + content[c.start_byte:c.end_byte].decode(errors="replace")
                    break
                break
            if declarator.type in ("pointer_declarator", "reference_declarator", "parenthesized_declarator"):
                declarator = declarator.child_by_field_name("declarator")
                continue
            break
    for child in node.children:
        if child.type == "identifier":
            return content[child.start_byte:child.end_byte].decode(errors="replace")
    return "<anonymous>"
