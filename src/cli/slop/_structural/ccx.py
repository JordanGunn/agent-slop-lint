"""CCX kernel - Cyclomatic and Cognitive Complexity metrics.

Computes McCabe Cyclomatic Complexity (CCX, 1976) and Campbell Cognitive
Complexity (CogC, 2018) per function across a codebase, in a single
tree-sitter AST traversal per file.

Direct AST traversal (not query_kernel) because both metrics require
containment-aware analysis: each decision point must be assigned to its
enclosing function, and Cognitive Complexity additionally needs the
nesting depth at each decision point.
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
class FunctionMetrics:
    """Cyclomatic and Cognitive complexity for one function."""

    name: str                  # function name (or "<lambda>", "<anonymous>")
    file: str                  # relative path from root
    path: str                  # absolute filesystem path
    line: int                  # 1-based start line of function definition
    end_line: int              # 1-based end line
    language: str
    ccx: int                   # Cyclomatic complexity (>= 1)
    cog: int                   # Cognitive complexity (>= 0)
    zone: str                  # "simple"|"moderate"|"complex"|"untestable"|"unknown"
    interpretation: str        # human-readable one-line verdict


@dataclass
class FileMetrics:
    """File-level CCX/CogC aggregation."""

    file: str                  # relative path
    path: str                  # absolute path
    language: str
    function_count: int
    max_ccx: int               # 0 if function_count == 0
    mean_ccx: float | None     # None if function_count == 0
    sum_ccx: int
    max_cog: int
    mean_cog: float | None
    sum_cog: int
    untestable_count: int      # functions with ccx > 50


@dataclass
class CcxResult:
    """Aggregated CCX/CogC result."""

    functions: list[FunctionMetrics]   # sorted by ccx desc, then cog desc
    files: list[FileMetrics]           # sorted by max_ccx desc
    languages: dict[str, int]          # {"python": 142, "go": 37}
    files_searched: int
    functions_analyzed: int
    zone_counts: dict[str, int]
    guidance: list[str]
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


# ---------------------------------------------------------------------------
# Per-language callables — name extraction and function-node matching
# ---------------------------------------------------------------------------

NameExtractor = Callable[[Any, bytes], str]
FunctionNodeMatcher = Callable[[Any, "_LangConfig"], bool]


def _default_name_extractor(node, content: bytes) -> str:
    """Standard function-name extraction via the ``name`` field.

    Languages that expose their function name through
    ``child_by_field_name("name")`` use this. Anonymous function shapes
    (`lambda`, `arrow_function_expression`, `do_clause`) return
    ``"<lambda>"``.
    """
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    if node.type in ("lambda", "arrow_function_expression", "do_clause"):
        return "<lambda>"
    return "<anonymous>"


def _default_is_function_node(node, config: "_LangConfig") -> bool:
    """Standard function-node check: node type is in ``config.function_nodes``."""
    return node.type in config.function_nodes


def _julia_find_call(node):
    """Find the call_expression that names a Julia function or method.

    Handles full-form ``function f(x) ... end``, where-clause
    ``function f(x) where T ... end``, and short-form ``f(x) = expr``
    (assignment with a call_expression LHS).
    """
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
    """Julia-specific name extraction.

    Uses ``_julia_find_call`` to locate the call_expression that holds
    the function name. The first relevant child of the call_expression
    is the name, with three shapes:

    - ``identifier``: regular name (`f` from `function f(x) ... end`).
    - ``operator``: operator-method definition (`+` from `+(a, b) = ...`).
    - ``field_expression``: dotted method extension (`show` from
      `function Base.show(...)` — the rightmost identifier).

    Anonymous forms (``arrow_function_expression``, ``do_clause``)
    return ``"<lambda>"``.
    """
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


def _julia_is_function_node(node, config: "_LangConfig") -> bool:
    """Julia function-node check: stock types plus short-form assignments.

    Short-form ``f(x) = ...`` parses as ``assignment`` whose first
    child is a ``call_expression``. Variable assignments like ``x = 1``
    have an ``identifier`` LHS and are not counted.
    """
    if node.type in config.function_nodes:
        return True
    if node.type == "assignment" and node.children:
        return node.children[0].type == "call_expression"
    return False


def _c_find_function_identifier(node):
    """Walk a C ``function_definition``'s declarator chain to the identifier.

    Tree-sitter-c parses ``int f(...) {...}`` as ``function_definition``
    with a ``declarator`` field. The chain to the function's name is:

    - plain                → ``function_declarator → identifier``
    - pointer return       → ``pointer_declarator → function_declarator → identifier``
    - ``static``/``inline``→ same chain (qualifiers are siblings, not wrappers)

    Function-pointer typedefs (``typedef int (*f)(int);``) parse as
    ``type_definition``, not ``function_definition``, so they never
    reach this routine. Function-returning-function-pointer
    (``int (*f())(int)``) is rare in real C and falls back to
    ``"<anonymous>"`` rather than handled exhaustively.
    """
    declarator = node.child_by_field_name("declarator")
    for _ in range(6):  # bound; real-world C pointer chains are shallow
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
    """C-specific function-name extraction.

    tree-sitter-c exposes the function name through the declarator
    chain, not a ``name`` field, so the default extractor returns
    ``"<anonymous>"`` for every C function. See
    ``_c_find_function_identifier`` for the chain shape.
    """
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
class _LangConfig:
    """Per-language tree-sitter node-type strategy for ccx."""

    function_nodes: frozenset[str]      # types that mark function/method/lambda definitions
    decision_nodes: frozenset[str]      # types that count as +1 for CCX
    nesting_nodes: frozenset[str]       # types that increment Cognitive nesting depth
    boolean_op_node: str                # node type for short-circuit operators
    boolean_op_filter: frozenset[str] | None  # operator strings to count, None = count all
    # Decisions that are syntactically children of a nesting node (e.g. elif of
    # if, switch_case of switch, match_arm of match) but conceptually live at
    # the same logical depth. Their cog increment uses depth-1 to compensate.
    compensating_decisions: frozenset[str] = frozenset()
    # Per-language callables. Defaults match the conventional tree-sitter
    # shape; languages whose AST diverges register their own.
    name_extractor: NameExtractor = _default_name_extractor
    is_function_node: FunctionNodeMatcher = _default_is_function_node


_LANG_CONFIG: dict[str, _LangConfig] = {
    "python": _LangConfig(
        function_nodes=frozenset({
            "function_definition",
            "lambda",
        }),
        decision_nodes=frozenset({
            "if_statement",
            "elif_clause",
            "for_statement",
            "while_statement",
            "except_clause",
            "conditional_expression",   # x if cond else y
            "case_clause",              # match/case (PEP 634)
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement",
            "while_statement",
            "except_clause",
            "conditional_expression",
            "match_statement",          # container for case_clause
        }),
        compensating_decisions=frozenset({
            "elif_clause",              # at same level as enclosing if
            "case_clause",              # at same level as match's surroundings
        }),
        boolean_op_node="boolean_operator",
        boolean_op_filter=None,         # Python: every boolean_operator counts
    ),
    "javascript": _LangConfig(
        function_nodes=frozenset({
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
            "generator_function_declaration",
            "generator_function",
        }),
        decision_nodes=frozenset({
            "if_statement",
            "for_statement",
            "for_in_statement",
            "for_of_statement",
            "while_statement",
            "do_statement",
            "switch_case",
            "catch_clause",
            "ternary_expression",
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement",
            "for_in_statement",
            "for_of_statement",
            "while_statement",
            "do_statement",
            "switch_statement",         # container for switch_case
            "catch_clause",
            "ternary_expression",
        }),
        compensating_decisions=frozenset({
            "switch_case",
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||", "??"}),
    ),
    "typescript": _LangConfig(
        function_nodes=frozenset({
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
            "generator_function_declaration",
            "generator_function",
        }),
        decision_nodes=frozenset({
            "if_statement",
            "for_statement",
            "for_in_statement",
            "for_of_statement",
            "while_statement",
            "do_statement",
            "switch_case",
            "catch_clause",
            "ternary_expression",
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement",
            "for_in_statement",
            "for_of_statement",
            "while_statement",
            "do_statement",
            "switch_statement",
            "catch_clause",
            "ternary_expression",
        }),
        compensating_decisions=frozenset({
            "switch_case",
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||", "??"}),
    ),
    "go": _LangConfig(
        function_nodes=frozenset({
            "function_declaration",
            "method_declaration",
            "func_literal",
        }),
        decision_nodes=frozenset({
            "if_statement",
            "for_statement",
            "expression_case",
            "type_case",
            "communication_case",
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement",
            "expression_switch_statement",
            "type_switch_statement",
            "select_statement",
        }),
        compensating_decisions=frozenset({
            "expression_case",
            "type_case",
            "communication_case",
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||"}),
    ),
    "rust": _LangConfig(
        function_nodes=frozenset({
            "function_item",
            "closure_expression",
        }),
        decision_nodes=frozenset({
            "if_expression",
            "while_expression",
            "for_expression",
            "match_arm",
        }),
        nesting_nodes=frozenset({
            "if_expression",
            "while_expression",
            "for_expression",
            "match_expression",         # container for match_arm
        }),
        compensating_decisions=frozenset({
            "match_arm",
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||"}),
    ),
    "java": _LangConfig(
        function_nodes=frozenset({
            "method_declaration",
            "constructor_declaration",
            "lambda_expression",
        }),
        decision_nodes=frozenset({
            "if_statement",
            "for_statement",
            "enhanced_for_statement",
            "while_statement",
            "do_statement",
            "switch_label",             # case label in classic switch_statement
            "switch_rule",              # arrow rule in modern switch_expression
            "catch_clause",
            "ternary_expression",
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement",
            "enhanced_for_statement",
            "while_statement",
            "do_statement",
            "switch_statement",         # classic container
            "switch_expression",        # Java 14+ container
            "catch_clause",
            "ternary_expression",
        }),
        compensating_decisions=frozenset({
            "switch_label",
            "switch_rule",
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||"}),
    ),
    "c_sharp": _LangConfig(
        function_nodes=frozenset({
            "method_declaration", "constructor_declaration",
            "lambda_expression",
        }),
        decision_nodes=frozenset({
            "if_statement",
            "for_statement", "foreach_statement",
            "while_statement", "do_statement",
            "switch_section",
            "catch_clause",
            "conditional_expression",
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement", "foreach_statement",
            "while_statement", "do_statement",
            "switch_statement",
            "catch_clause",
            "conditional_expression",
        }),
        compensating_decisions=frozenset({
            "switch_section",
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||"}),
    ),
    "julia": _LangConfig(
        function_nodes=frozenset({
            "function_definition",
            "arrow_function_expression",
            "do_clause",       # `map(xs) do x ... end` body
        }),
        decision_nodes=frozenset({
            "if_statement",
            "elseif_clause",
            "for_statement",
            "while_statement",
            "catch_clause",
            "ternary_expression",
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement",
            "while_statement",
            "try_statement",   # container for catch/finally clauses
            "catch_clause",
            "ternary_expression",
        }),
        compensating_decisions=frozenset({
            "elseif_clause",   # syntactically inside if_statement
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||"}),
        name_extractor=_julia_name_extractor,
        is_function_node=_julia_is_function_node,
    ),
    "c": _LangConfig(
        function_nodes=frozenset({"function_definition"}),
        decision_nodes=frozenset({
            "if_statement",
            "for_statement",
            "while_statement",
            "do_statement",
            "case_statement",          # both `case X:` and `default:`
            "conditional_expression",  # ternary `?:`
        }),
        nesting_nodes=frozenset({
            "if_statement",
            "for_statement",
            "while_statement",
            "do_statement",
            "switch_statement",        # container for case_statement
            "conditional_expression",
        }),
        compensating_decisions=frozenset({
            "case_statement",          # syntactically inside switch_statement
        }),
        boolean_op_node="binary_expression",
        boolean_op_filter=frozenset({"&&", "||"}),
        name_extractor=_c_name_extractor,
    ),
}

# Glob patterns per language for find_kernel discovery.
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

# Bash files are explicitly excluded — see 03_POLICIES.md.
_EXCLUDED_LANGUAGES: frozenset[str] = frozenset({"bash"})


# ---------------------------------------------------------------------------
# Walker state
# ---------------------------------------------------------------------------

@dataclass
class _WalkState:
    """Mutable accumulator for one function's CCX and CogC."""

    ccx: int = 1   # base path
    cog: int = 0


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------

def _compute_zone(ccx: int, thresholds: tuple[int, int, int]) -> str:
    """Classify a function by its CCX score.

    thresholds = (simple_max, moderate_max, complex_max).
    Default (10, 20, 50) follows McCabe's classic recommendation plus the
    SEI/NIST practitioner consensus that CCX > 50 is effectively untestable.
    """
    simple_max, moderate_max, complex_max = thresholds
    if ccx <= simple_max:
        return "simple"
    if ccx <= moderate_max:
        return "moderate"
    if ccx <= complex_max:
        return "complex"
    return "untestable"


def _interpret(ccx: int, cog: int, zone: str) -> str:
    """Generate a human-readable one-line verdict for a function."""
    # Note Cognitive divergence when it's notably higher than Cyclomatic.
    if ccx >= 3 and cog >= ccx * 1.5:
        cog_note = f", CogC={cog} (heavy nesting)"
    elif cog != ccx:
        cog_note = f", CogC={cog}"
    else:
        cog_note = ""

    if zone == "simple":
        return (
            f"Simple (CCX={ccx}{cog_note}). Low cyclomatic complexity — "
            f"straightforward to test and reason about."
        )
    if zone == "moderate":
        return (
            f"Moderate (CCX={ccx}{cog_note}). More paths than ideal — "
            f"test coverage effort grows linearly with branches."
        )
    if zone == "complex":
        return (
            f"Complex (CCX={ccx}{cog_note}). Refactor candidate — extract "
            f"helper functions or flatten nested conditionals."
        )
    if zone == "untestable":
        return (
            f"Untestable (CCX={ccx}{cog_note}). Exhaustive path coverage "
            f"is impractical. Split this function into independently "
            f"testable parts."
        )
    return f"Unknown (CCX={ccx})"


# ---------------------------------------------------------------------------
# AST parsing helper
# ---------------------------------------------------------------------------

def _parse_file(
    file_path: Path,
    language: str,
) -> tuple[Any, bytes, str | None]:
    """Parse a file with tree-sitter.

    Returns (tree, content_bytes, error_or_none). On error, tree is None.
    """
    lang = load_language(language)
    if lang is None:
        return None, b"", f"{file_path}: tree-sitter grammar unavailable for '{language}'"

    try:
        content = file_path.read_bytes()
    except Exception as e:
        return None, b"", f"{file_path}: read error: {e}"

    try:
        parser = tree_sitter.Parser(lang)
        tree = parser.parse(content)
        return tree, content, None
    except Exception as e:
        return None, b"", f"{file_path}: parse error: {e}"


def _node_text(node, content: bytes) -> str:
    """Extract source text for a tree-sitter node."""
    return content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_function_name(node, content: bytes, config: _LangConfig) -> str:
    """Delegate to the per-language ``name_extractor`` callable on ``config``."""
    return config.name_extractor(node, content)


def _python_bool_op(node) -> str:
    """Extract the operator text ('and'/'or') from a Python boolean_operator node."""
    for child in node.children:
        if child.type in ("and", "or"):
            return child.type
    return ""


def _binary_op_text(node, content: bytes) -> str:
    """Extract the operator text from a binary_expression node.

    Most grammars expose the operator as a named field. Julia exposes it
    as a positional child of type ``operator``; fall back to that when no
    field is present.
    """
    op_node = node.child_by_field_name("operator")
    if op_node is not None:
        return _node_text(op_node, content)
    for child in node.children:
        if child.type == "operator":
            return _node_text(child, content)
    return ""


# ---------------------------------------------------------------------------
# Walker
# ---------------------------------------------------------------------------

def _walk_function(
    func_node,
    content: bytes,
    config: _LangConfig,
    file_path: Path,
    rel_file: str,
    language: str,
    thresholds: tuple[int, int, int],
    out_functions: list[FunctionMetrics],
) -> None:
    """Walk one function definition node, computing CCX/CogC and emitting a FunctionMetrics."""
    name = _extract_function_name(func_node, content, config)
    state = _WalkState()

    def walk(node, depth: int) -> None:
        node_type = node.type

        # Nested function definition: handle as a separate FunctionMetrics
        # and stop descending — its body is the new function's responsibility.
        if config.is_function_node(node, config) and node is not func_node:
            _walk_function(
                node, content, config, file_path, rel_file,
                language, thresholds, out_functions,
            )
            return

        # Decision-point check (CCX += 1, CogC += 1 + nesting_depth)
        if node_type in config.decision_nodes:
            state.ccx += 1
            # Compensating decisions (elif of if, switch_case of switch, etc.)
            # are syntactically children of a nesting node but conceptually live
            # at the same logical depth as it. Subtract one to compensate for
            # the parent's nesting bump.
            if node_type in config.compensating_decisions:
                state.cog += 1 + max(0, depth - 1)
            else:
                state.cog += 1 + depth

        # Boolean operator handling
        if node_type == config.boolean_op_node:
            if config.boolean_op_filter is None:
                # Python: every boolean_operator is a counted short-circuit op
                is_short_circuit = True
                node_op = _python_bool_op(node)
            else:
                # Other languages: filter binary_expression by operator text
                node_op = _binary_op_text(node, content)
                is_short_circuit = node_op in config.boolean_op_filter

            if is_short_circuit:
                state.ccx += 1
                # CogC sequence collapsing: only count if not continuing a
                # same-operator chain with the parent.
                parent = node.parent
                in_continuing_sequence = False
                if parent is not None and parent.type == config.boolean_op_node:
                    if config.boolean_op_filter is None:
                        parent_op = _python_bool_op(parent)
                        in_continuing_sequence = (parent_op == node_op)
                    else:
                        parent_op = _binary_op_text(parent, content)
                        if parent_op in config.boolean_op_filter:
                            in_continuing_sequence = (parent_op == node_op)
                if not in_continuing_sequence:
                    state.cog += 1

        # Determine new depth for children
        new_depth = depth + 1 if node_type in config.nesting_nodes else depth

        # Recurse
        for child in node.children:
            walk(child, new_depth)

    # Walk the function's body. Most languages put the body in a 'body' field;
    # if not, walk all children of the function node directly.
    body = func_node.child_by_field_name("body")
    if body is not None:
        walk(body, 0)
    else:
        for child in func_node.children:
            walk(child, 0)

    # Enforce CCX >= 1 invariant
    ccx = max(1, state.ccx)
    cog = max(0, state.cog)
    zone = _compute_zone(ccx, thresholds)
    interpretation = _interpret(ccx, cog, zone)

    out_functions.append(FunctionMetrics(
        name=name,
        file=rel_file,
        path=str(file_path),
        line=func_node.start_point[0] + 1,
        end_line=func_node.end_point[0] + 1,
        language=language,
        ccx=ccx,
        cog=cog,
        zone=zone,
        interpretation=interpretation,
    ))


def _walk_file(
    file_path: Path,
    language: str,
    root: Path,
    thresholds: tuple[int, int, int],
) -> tuple[list[FunctionMetrics], list[str]]:
    """Walk one file's AST and extract per-function metrics."""
    config = _LANG_CONFIG.get(language)
    if config is None:
        return [], []  # Language not configured for ccx, skip silently

    tree, content, error = _parse_file(file_path, language)
    if tree is None:
        return [], [error] if error is not None else []

    functions: list[FunctionMetrics] = []
    rel_file = _relative_path(root, file_path)

    def find_functions(node) -> None:
        if config.is_function_node(node, config):
            _walk_function(
                node, content, config, file_path, rel_file,
                language, thresholds, functions,
            )
            return  # Don't descend; the function's body is handled by _walk_function
        for child in node.children:
            find_functions(child)

    find_functions(tree.root_node)
    return functions, []


# ---------------------------------------------------------------------------
# File-level aggregation
# ---------------------------------------------------------------------------

def _aggregate_file_metrics(
    functions: list[FunctionMetrics],
) -> dict[str, FileMetrics]:
    """Group functions by file and compute per-file aggregates."""
    by_file: dict[str, list[FunctionMetrics]] = {}
    for fn in functions:
        by_file.setdefault(fn.file, []).append(fn)

    result: dict[str, FileMetrics] = {}
    for rel_file, fns in by_file.items():
        ccx_values = [f.ccx for f in fns]
        cog_values = [f.cog for f in fns]
        result[rel_file] = FileMetrics(
            file=rel_file,
            path=fns[0].path if fns else "",
            language=fns[0].language if fns else "",
            function_count=len(fns),
            max_ccx=max(ccx_values) if ccx_values else 0,
            mean_ccx=(sum(ccx_values) / len(ccx_values)) if ccx_values else None,
            sum_ccx=sum(ccx_values),
            max_cog=max(cog_values) if cog_values else 0,
            mean_cog=(sum(cog_values) / len(cog_values)) if cog_values else None,
            sum_cog=sum(cog_values),
            untestable_count=sum(1 for c in ccx_values if c > 50),
        )
    return result


# ---------------------------------------------------------------------------
# Main kernel entry point
# ---------------------------------------------------------------------------

def ccx_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
    min_ccx: int = 1,
    thresholds: tuple[int, int, int] = (10, 20, 50),
) -> CcxResult:
    """Compute Cyclomatic and Cognitive complexity per function across a codebase.

    Args:
        root: Search root directory
        languages: Subset of supported languages to analyze; None = all supported
        globs: Override glob patterns (otherwise derived from languages)
        excludes: Exclude glob patterns
        hidden: Include hidden files
        no_ignore: Don't respect gitignore
        max_results: Cap on functions in output (post-sort truncation)
        min_ccx: Filter — only return functions with ccx >= this value
        thresholds: (simple_max, moderate_max, complex_max) zone boundaries

    Returns:
        CcxResult with per-function metrics sorted by ccx desc.
    """
    errors: list[str] = []

    # Step 1: Determine active languages
    if languages is None:
        active_languages = set(_LANG_CONFIG.keys())
    else:
        active_languages = set(lang.lower() for lang in languages)
        unsupported = active_languages - set(_LANG_CONFIG.keys())
        if unsupported:
            return CcxResult(
                functions=[],
                files=[],
                languages={},
                files_searched=0,
                functions_analyzed=0,
                zone_counts=_empty_zone_counts(),
                guidance=[],
                errors=[
                    f"Unsupported languages: {sorted(unsupported)}. "
                    f"Supported: {sorted(_LANG_CONFIG.keys())}"
                ],
            )

    # Step 2: Build globs (caller-specified overrides language defaults)
    if globs:
        find_globs = list(globs)
    else:
        find_globs = []
        for lang in sorted(active_languages):
            find_globs.extend(_LANG_GLOBS.get(lang, []))

    # Step 3: Discover files
    find_result = find_kernel(
        root=root,
        globs=find_globs,
        excludes=excludes,
        hidden=hidden,
        no_ignore=no_ignore,
    )
    errors.extend(find_result.errors)

    file_paths = [root / Path(e.path) for e in find_result.entries if e.type == "file"]

    # Step 4: Walk each file
    all_functions: list[FunctionMetrics] = []
    language_counts: dict[str, int] = {}

    for file_path in file_paths:
        lang = detect_language(file_path)
        if lang is None:
            continue
        if lang in _EXCLUDED_LANGUAGES:
            continue
        if lang not in _LANG_CONFIG:
            continue
        if lang not in active_languages:
            continue

        funcs, file_errors = _walk_file(file_path, lang, root, thresholds)
        all_functions.extend(funcs)
        errors.extend(file_errors)
        if funcs:
            language_counts[lang] = language_counts.get(lang, 0) + len(funcs)

    # Step 5: Apply min_ccx filter
    if min_ccx > 1:
        all_functions = [f for f in all_functions if f.ccx >= min_ccx]

    functions_analyzed_total = len(all_functions)

    # Step 6: Sort by ccx desc, then cog desc, then file/line for stability
    all_functions.sort(key=lambda f: (-f.ccx, -f.cog, f.file, f.line))

    # Step 7: Apply max_results truncation
    truncated = False
    if max_results is not None and len(all_functions) > max_results:
        all_functions = all_functions[:max_results]
        truncated = True

    # Step 8: Per-file aggregation (over the truncated set)
    file_metrics_map = _aggregate_file_metrics(all_functions)
    file_metrics_list = sorted(
        file_metrics_map.values(),
        key=lambda fm: (-fm.max_ccx, fm.file),
    )

    # Step 9: Zone counts
    zone_counts = _count_zones(all_functions)

    # Step 10: Guidance
    guidance = _build_guidance(all_functions)

    return CcxResult(
        functions=all_functions,
        files=file_metrics_list,
        languages=language_counts,
        files_searched=find_result.total_found,
        functions_analyzed=functions_analyzed_total,
        zone_counts=zone_counts,
        guidance=guidance,
        errors=errors,
        truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Zone counting and guidance
# ---------------------------------------------------------------------------

_ZONE_LABELS: dict[str, str] = {
    "moderate": "Moderate",
    "complex": "Complex",
    "untestable": "Untestable",
}

_ZONE_ACTIONS: dict[str, str] = {
    "moderate": "Consider whether branches can be collapsed or extracted.",
    "complex": "Refactor candidate — extract helpers or flatten nested conditionals.",
    "untestable": "Split this function into independently testable parts.",
}


def _build_guidance(functions: list[FunctionMetrics]) -> list[str]:
    """Build guidance list — one entry per non-simple function."""
    items: list[str] = []
    for fn in functions:
        if fn.zone not in _ZONE_LABELS:
            continue
        label = _ZONE_LABELS[fn.zone]
        action = _ZONE_ACTIONS.get(fn.zone, "Review this function.")
        items.append(
            f"{fn.file}:{fn.line} {fn.name} ({label}): "
            f"CCX={fn.ccx}, CogC={fn.cog}. {action}"
        )
    return items


def _count_zones(functions: list[FunctionMetrics]) -> dict[str, int]:
    """Count functions per zone."""
    zones = ("simple", "moderate", "complex", "untestable", "unknown")
    counts: dict[str, int] = {z: 0 for z in zones}
    for fn in functions:
        counts[fn.zone] = counts.get(fn.zone, 0) + 1
    return counts


def _empty_zone_counts() -> dict[str, int]:
    return {"simple": 0, "moderate": 0, "complex": 0, "untestable": 0, "unknown": 0}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _relative_path(root: Path, path: Path) -> str:
    """Return relative path string, or abs path if not relative to root."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
