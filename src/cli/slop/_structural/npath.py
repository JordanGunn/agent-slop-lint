"""NPATH kernel — acyclic execution path complexity per function.

Computes Nejmeh's (1988) NPATH metric: the count of acyclic execution
paths through a function. Unlike McCabe's CCX (additive: 1 + branches),
NPATH is multiplicative: sequential branches multiply path counts.
This catches combinatorial explosion that CCX underreports.

Example: 10 sequential ifs → CCX=11, NPATH=1024.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import tree_sitter

from slop._fs.find import find_kernel
from slop._ast.treesitter import detect_language, load_language

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class NpathMetrics:
    """NPATH complexity for one function."""

    name: str
    file: str
    path: str
    line: int
    end_line: int
    language: str
    npath: int


@dataclass
class NpathResult:
    """Aggregated NPATH result."""

    functions: list[NpathMetrics]
    files_searched: int
    functions_analyzed: int
    languages: dict[str, int]
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


# ---------------------------------------------------------------------------
# Per-language callables — name extraction and function-node matching
# ---------------------------------------------------------------------------

NameExtractor = Callable[[Any, bytes], str]
FunctionNodeMatcher = Callable[[Any, "_NpathLangConfig"], bool]


def _default_name_extractor(node, content: bytes) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    if node.type in ("lambda", "arrow_function_expression", "do_clause"):
        return "<lambda>"
    return "<anonymous>"


def _default_is_function_node(node, config: "_NpathLangConfig") -> bool:
    return node.type in config.function_nodes


def _julia_find_call(node):
    """Find the call_expression that names a Julia function or method."""
    if node.type == "function_definition":
        for child in node.children:
            if child.type == "signature":
                for sub in child.children:
                    if sub.type == "call_expression":
                        return sub
                    if sub.type == "where_expression":
                        for ssub in sub.children:
                            if ssub.type == "call_expression":
                                return ssub
        return None
    if node.type == "assignment" and node.children:
        lhs = node.children[0]
        if lhs.type == "call_expression":
            return lhs
    return None


def _julia_name_extractor(node, content: bytes) -> str:
    """Julia-specific name extraction. See `slop._structural.ccx` for details."""
    if node.type in ("arrow_function_expression", "do_clause"):
        return "<lambda>"
    call = _julia_find_call(node)
    if call is None:
        return "<anonymous>"
    for c in call.children:
        if c.type in ("identifier", "operator"):
            return content[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
        if c.type == "field_expression":
            idents = [fc for fc in c.children if fc.type == "identifier"]
            if idents:
                last = idents[-1]
                return content[last.start_byte:last.end_byte].decode("utf-8", errors="replace")
            return content[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
        if c.type == "argument_list":
            break
    return "<anonymous>"


def _julia_is_function_node(node, config: "_NpathLangConfig") -> bool:
    """Julia: stock function nodes plus short-form assignments."""
    if node.type in config.function_nodes:
        return True
    if node.type == "assignment" and node.children:
        return node.children[0].type == "call_expression"
    return False


def _c_find_function_identifier(node):
    """Walk a C ``function_definition``'s declarator chain to the identifier.

    See ``slop._structural.ccx._c_find_function_identifier`` for the
    chain shapes covered.
    """
    declarator = node.child_by_field_name("declarator")
    for _ in range(6):
        if declarator is None:
            return None
        if declarator.type == "function_declarator":
            inner = declarator.child_by_field_name("declarator")
            if inner is not None and inner.type == "identifier":
                return inner
            return None
        if declarator.type in ("pointer_declarator", "parenthesized_declarator"):
            declarator = declarator.child_by_field_name("declarator")
            continue
        break
    return None


def _c_name_extractor(node, content: bytes) -> str:
    """C-specific name extraction. See `slop._structural.ccx` for details."""
    if node.type != "function_definition":
        return "<anonymous>"
    ident = _c_find_function_identifier(node)
    if ident is None:
        return "<anonymous>"
    return content[ident.start_byte:ident.end_byte].decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Per-language configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _NpathLangConfig:
    function_nodes: frozenset[str]
    if_node: str                    # "if_statement" etc.
    else_clause: str                # "else_clause" etc.
    elif_clause: str | None         # "elif_clause" (Python) or None
    loop_nodes: frozenset[str]      # for, while, do-while
    switch_node: str | None         # "switch_statement" etc.
    case_node: str | None           # "switch_case", "case_clause" etc.
    try_node: str | None            # "try_statement" etc.
    catch_node: str | None          # "except_clause", "catch_clause" etc.
    body_field: str                 # "body", "consequence", etc.; "" for flat-body langs
    block_types: frozenset[str]     # block/statement_block types
    bare_else_keyword: str | None = None  # C#: "else" is a bare keyword, not a wrapper
    # Flat-body langs (Julia) have no body field and no block wrapper —
    # statements are direct children of the function/if/etc. node. Listing
    # the structural-keyword child types here lets the kernel walk the body
    # by iterating over children minus these. Empty for non-flat langs.
    body_skip_types: frozenset[str] = frozenset()
    # Wrapper node types between ``switch_node`` and ``case_node``. Some
    # grammars (Java's ``switch_block`` / ``switch_block_statement_group``,
    # C#'s ``switch_body``, C's ``compound_statement``) nest cases inside
    # one or more of these wrappers rather than as direct switch children.
    # Empty default preserves prior behaviour for languages that don't
    # need it (Python's ``match_statement``, JS/TS, Go, Rust).
    switch_body_types: frozenset[str] = frozenset()
    # Per-language callables. Defaults match the conventional tree-sitter
    # shape; languages whose AST diverges register their own.
    name_extractor: NameExtractor = _default_name_extractor
    is_function_node: FunctionNodeMatcher = _default_is_function_node


_LANG_CONFIG: dict[str, _NpathLangConfig] = {
    "python": _NpathLangConfig(
        function_nodes=frozenset({"function_definition", "lambda"}),
        if_node="if_statement",
        else_clause="else_clause",
        elif_clause="elif_clause",
        loop_nodes=frozenset({"for_statement", "while_statement"}),
        switch_node="match_statement",
        case_node="case_clause",
        try_node="try_statement",
        catch_node="except_clause",
        body_field="body",
        block_types=frozenset({"block"}),
    ),
    "javascript": _NpathLangConfig(
        function_nodes=frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "method_definition",
        }),
        if_node="if_statement",
        else_clause="else_clause",
        elif_clause=None,
        loop_nodes=frozenset({
            "for_statement", "for_in_statement", "for_of_statement",
            "while_statement", "do_statement",
        }),
        switch_node="switch_statement",
        case_node="switch_case",
        try_node="try_statement",
        catch_node="catch_clause",
        body_field="body",
        block_types=frozenset({"statement_block"}),
    ),
    "typescript": _NpathLangConfig(
        function_nodes=frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "method_definition",
        }),
        if_node="if_statement",
        else_clause="else_clause",
        elif_clause=None,
        loop_nodes=frozenset({
            "for_statement", "for_in_statement", "for_of_statement",
            "while_statement", "do_statement",
        }),
        switch_node="switch_statement",
        case_node="switch_case",
        try_node="try_statement",
        catch_node="catch_clause",
        body_field="body",
        block_types=frozenset({"statement_block"}),
    ),
    "go": _NpathLangConfig(
        function_nodes=frozenset({
            "function_declaration", "method_declaration", "func_literal",
        }),
        if_node="if_statement",
        else_clause="else_clause",
        elif_clause=None,
        loop_nodes=frozenset({"for_statement"}),
        switch_node="expression_switch_statement",
        case_node="expression_case",
        try_node=None,
        catch_node=None,
        body_field="body",
        block_types=frozenset({"block"}),
    ),
    "rust": _NpathLangConfig(
        function_nodes=frozenset({"function_item", "closure_expression"}),
        if_node="if_expression",
        else_clause="else_clause",
        elif_clause=None,
        loop_nodes=frozenset({
            "for_expression", "while_expression", "loop_expression",
        }),
        switch_node="match_expression",
        case_node="match_arm",
        try_node=None,
        catch_node=None,
        body_field="body",
        block_types=frozenset({"block"}),
    ),
    "java": _NpathLangConfig(
        function_nodes=frozenset({
            "method_declaration", "constructor_declaration",
            "lambda_expression",
        }),
        if_node="if_statement",
        else_clause="else_clause",
        elif_clause=None,
        loop_nodes=frozenset({
            "for_statement", "enhanced_for_statement",
            "while_statement", "do_statement",
        }),
        switch_node="switch_statement",
        case_node="switch_label",
        try_node="try_statement",
        catch_node="catch_clause",
        body_field="body",
        block_types=frozenset({"block"}),
        switch_body_types=frozenset({
            "switch_block", "switch_block_statement_group",
        }),
    ),
    "c_sharp": _NpathLangConfig(
        function_nodes=frozenset({
            "method_declaration", "constructor_declaration",
            "lambda_expression",
        }),
        if_node="if_statement",
        else_clause="__none__",        # C# has no else_clause wrapper
        elif_clause=None,
        loop_nodes=frozenset({
            "for_statement", "foreach_statement",
            "while_statement", "do_statement",
        }),
        switch_node="switch_statement",
        case_node="switch_section",
        try_node="try_statement",
        catch_node="catch_clause",
        body_field="body",
        block_types=frozenset({"block"}),
        bare_else_keyword="else",
        switch_body_types=frozenset({"switch_body"}),
    ),
    "julia": _NpathLangConfig(
        function_nodes=frozenset({
            "function_definition",
            "arrow_function_expression",
            "do_clause",       # `map(xs) do x ... end` body
        }),
        if_node="if_statement",
        else_clause="else_clause",
        elif_clause="elseif_clause",
        loop_nodes=frozenset({"for_statement", "while_statement"}),
        switch_node=None,
        case_node=None,
        try_node="try_statement",
        catch_node="catch_clause",
        body_field="",                 # flat-body language
        block_types=frozenset(),
        body_skip_types=frozenset({
            "function", "end", "signature",
            "if", "elseif", "else", "for", "for_binding",
            "while", "try", "catch", "finally", "do",
        }),
        name_extractor=_julia_name_extractor,
        is_function_node=_julia_is_function_node,
    ),
    "c": _NpathLangConfig(
        function_nodes=frozenset({"function_definition"}),
        if_node="if_statement",
        else_clause="else_clause",
        elif_clause=None,                  # else-if = nested if_statement
        loop_nodes=frozenset({
            "while_statement", "do_statement", "for_statement",
        }),
        switch_node="switch_statement",
        case_node="case_statement",        # both `case X:` and `default:`
        try_node=None,
        catch_node=None,
        body_field="body",
        block_types=frozenset({"compound_statement"}),
        switch_body_types=frozenset({"compound_statement"}),
        name_extractor=_c_name_extractor,
    ),
}

_LANG_GLOBS: dict[str, list[str]] = {
    "python": ["**/*.py"],
    "javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],
    "typescript": ["**/*.ts", "**/*.tsx"],
    "go": ["**/*.go"],
    "rust": ["**/*.rs"],
    "java": ["**/*.java"],
    "c_sharp": ["**/*.cs"],
    "julia": ["**/*.jl"],
    "c": ["**/*.c", "**/*.h"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_file(file_path: Path, language: str) -> tuple[Any, bytes, str | None]:
    lang = load_language(language)
    if lang is None:
        return None, b"", f"{file_path}: grammar unavailable for '{language}'"
    try:
        content = file_path.read_bytes()
    except Exception as e:
        return None, b"", f"{file_path}: read error: {e}"
    try:
        parser = tree_sitter.Parser(lang)
        return parser.parse(content), content, None
    except Exception as e:
        return None, b"", f"{file_path}: parse error: {e}"


def _node_text(node, content: bytes) -> str:
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _extract_function_name(node, content: bytes, config: _NpathLangConfig) -> str:
    """Delegate to the per-language ``name_extractor`` callable on ``config``."""
    return config.name_extractor(node, content)


def _npath_of_flat_body(node, config: _NpathLangConfig) -> int:
    """Compute NPATH for a flat-body construct (Julia function/if/loop body).

    Julia has no block-wrapper node; statements are direct children. This
    walks those children, skipping structural keyword nodes, and multiplies
    their NPATH contributions.
    """
    result = 1
    for child in node.children:
        if child.type in config.body_skip_types:
            continue
        cn = _npath_of_node(child, config)
        if cn > 1:
            result *= cn
    return result


# ---------------------------------------------------------------------------
# NPATH walker
# ---------------------------------------------------------------------------


def _npath_of_block(node, config: _NpathLangConfig) -> int:
    """Compute NPATH for a block of sequential statements.

    NPATH of a sequence = product of NPATH of each statement.
    """
    if node is None:
        return 1

    # If this is a block/statement_block, walk its children
    if node.type in config.block_types:
        result = 1
        for child in node.children:
            result *= _npath_of_node(child, config)
        return result

    # Single statement (not a block)
    return _npath_of_node(node, config)


def _npath_of_node(node, config: _NpathLangConfig) -> int:
    """Compute NPATH contribution of a single AST node."""
    ntype = node.type

    # --- if/elif ---
    if ntype == config.if_node:
        return _npath_of_if(node, config)

    # --- Python elif ---
    if config.elif_clause and ntype == config.elif_clause:
        return _npath_of_if(node, config)

    # --- loops (for, while, do) ---
    if ntype in config.loop_nodes:
        body = node.child_by_field_name(config.body_field)
        return _npath_of_block(body, config) + 1

    # --- switch/match ---
    if config.switch_node and ntype == config.switch_node:
        total = 0

        def _iter_cases(parent):
            """Yield case nodes, descending through any switch_body wrappers."""
            for child in parent.children:
                if config.case_node and child.type == config.case_node:
                    yield child
                elif child.type in config.switch_body_types:
                    yield from _iter_cases(child)

        for case_child in _iter_cases(node):
            # Each case contributes its body's NPATH (1 if inline / no block)
            case_npath = 1
            for cc in case_child.children:
                if cc.type in config.block_types:
                    case_npath = _npath_of_block(cc, config)
            total += case_npath
        return max(total, 1)

    # --- try/catch ---
    if config.try_node and ntype == config.try_node:
        try_body_npath = 1
        handler_sum = 0
        for child in node.children:
            if child.type in config.block_types:
                try_body_npath = _npath_of_block(child, config)
            elif config.catch_node and child.type == config.catch_node:
                catch_body = child.child_by_field_name(config.body_field)
                handler_sum += _npath_of_block(catch_body, config)
        if handler_sum == 0:
            return try_body_npath
        return try_body_npath + handler_sum

    # --- nested function: don't descend ---
    if config.is_function_node(node, config):
        return 1

    # --- anything else: transparent, recurse into children ---
    # For compound expressions / blocks that aren't statements
    result = 1
    for child in node.children:
        child_npath = _npath_of_node(child, config)
        if child_npath > 1:
            result *= child_npath
    return result


def _npath_of_if(node, config: _NpathLangConfig) -> int:
    """Compute NPATH of an if/elif/else chain.

    Each branch (then, elif*, else) contributes its body NPATH.
    Total = sum of all branch NPATHs.
    If no terminal else: +1 for the implicit fall-through path.
    """
    # Then branch
    then_npath = 1
    consequence = node.child_by_field_name("consequence")
    if consequence and consequence.type in config.block_types:
        then_npath = _npath_of_block(consequence, config)
    else:
        for child in node.children:
            if child.type in config.block_types:
                then_npath = _npath_of_block(child, config)
                break

    # Collect alternative branches (elif*, else)
    alt_npaths: list[int] = []
    has_terminal = False

    for child in node.children:
        if config.elif_clause and child.type == config.elif_clause:
            elif_body_npath = 1
            for ec in child.children:
                if ec.type in config.block_types:
                    elif_body_npath = _npath_of_block(ec, config)
            alt_npaths.append(elif_body_npath)
        elif child.type == config.else_clause:
            has_terminal = True
            else_npath_added = False
            for ec in child.children:
                if ec.type in config.block_types:
                    alt_npaths.append(_npath_of_block(ec, config))
                    else_npath_added = True
                elif ec.type == config.if_node:
                    # C-style else-if chain
                    alt_npaths.append(_npath_of_if(ec, config))
                    else_npath_added = True
            # Flat-body langs (Julia): no block wrapper inside else_clause.
            # Treat the clause as contributing one path; nested control flow
            # inside is not deeply analysed (documented limitation).
            if not else_npath_added and not config.body_field:
                alt_npaths.append(1)

    # Bare-keyword else (C#): "else" is a keyword child, body is next sibling
    if config.bare_else_keyword and not has_terminal:
        children = list(node.children)
        for i, child in enumerate(children):
            if child.type == config.bare_else_keyword and i + 1 < len(children):
                nxt = children[i + 1]
                has_terminal = True
                if nxt.type in config.block_types:
                    alt_npaths.append(_npath_of_block(nxt, config))
                elif nxt.type == config.if_node:
                    alt_npaths.append(_npath_of_if(nxt, config))

    if not has_terminal:
        # Implicit fall-through path
        return then_npath + sum(alt_npaths) + 1
    return then_npath + sum(alt_npaths)


# ---------------------------------------------------------------------------
# Main kernel
# ---------------------------------------------------------------------------


def npath_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
    min_npath: int = 1,
) -> NpathResult:
    """Compute NPATH acyclic execution path count per function."""
    errors: list[str] = []

    if languages:
        active = {l.lower() for l in languages} & set(_LANG_CONFIG)
    else:
        active = set(_LANG_CONFIG)
    if not active:
        return NpathResult(
            functions=[], files_searched=0, functions_analyzed=0,
            languages={},
            errors=[f"No supported languages. Supported: {sorted(_LANG_CONFIG)}"],
        )

    if globs:
        find_globs = list(globs)
    else:
        find_globs = []
        for lang in sorted(active):
            find_globs.extend(_LANG_GLOBS.get(lang, []))

    find_result = find_kernel(
        root=root, globs=find_globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    )
    errors.extend(find_result.errors)
    file_paths = [root / e.path for e in find_result.entries if e.type == "file"]

    all_functions: list[NpathMetrics] = []
    language_counts: dict[str, int] = {}

    for fp in file_paths:
        lang = detect_language(fp)
        if lang is None or lang not in active or lang not in _LANG_CONFIG:
            continue
        config = _LANG_CONFIG[lang]

        tree, content, err = _parse_file(fp, lang)
        if tree is None:
            if err:
                errors.append(err)
            continue

        rel = _relative_path(root, fp)

        def find_functions(node):
            if config.is_function_node(node, config):
                name = _extract_function_name(node, content, config)
                if config.body_field:
                    body = node.child_by_field_name(config.body_field)
                    npath = _npath_of_block(body, config)
                else:
                    npath = _npath_of_flat_body(node, config)
                npath = max(1, npath)

                if npath >= min_npath:
                    all_functions.append(NpathMetrics(
                        name=name, file=rel, path=str(fp),
                        line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        language=lang,
                        npath=npath,
                    ))
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                return
            for child in node.children:
                find_functions(child)

        find_functions(tree.root_node)

    all_functions.sort(key=lambda f: (-f.npath, f.file, f.line))

    truncated = False
    if max_results is not None and len(all_functions) > max_results:
        all_functions = all_functions[:max_results]
        truncated = True

    return NpathResult(
        functions=all_functions,
        files_searched=find_result.total_found,
        functions_analyzed=len(all_functions),
        languages=language_counts,
        errors=errors,
        truncated=truncated,
    )
