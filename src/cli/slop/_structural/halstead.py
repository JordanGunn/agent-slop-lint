"""Halstead kernel — Software Science token metrics per function.

Computes Halstead's (1977) derived metrics from operator/operand counts:
Volume (information content), Difficulty (cognitive burden), and Effort.
Operators are keywords and symbols; operands are identifiers and literals.
Classification is per-language via tree-sitter leaf node types.
"""

from __future__ import annotations

import math
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
class HalsteadMetrics:
    """Halstead metrics for one function."""

    name: str
    file: str
    path: str
    line: int
    end_line: int
    language: str
    n1: int              # unique operators
    n2: int              # unique operands
    total_n1: int        # total operator occurrences (N1)
    total_n2: int        # total operand occurrences (N2)
    vocabulary: int      # n1 + n2
    length: int          # N1 + N2
    volume: float        # Length * log2(Vocabulary)
    difficulty: float    # (n1/2) * (N2/n2)
    effort: float        # Difficulty * Volume


@dataclass
class HalsteadResult:
    """Aggregated Halstead result."""

    functions: list[HalsteadMetrics]
    files_searched: int
    functions_analyzed: int
    languages: dict[str, int]
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


# ---------------------------------------------------------------------------
# Per-language callables — name extraction and function-node matching
# ---------------------------------------------------------------------------

NameExtractor = Callable[[Any, bytes], str]
FunctionNodeMatcher = Callable[[Any, "_HalsteadLangConfig"], bool]


def _default_name_extractor(node, content: bytes) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return content[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
    if node.type in ("lambda", "arrow_function_expression", "do_clause"):
        return "<lambda>"
    return "<anonymous>"


def _default_is_function_node(node, config: "_HalsteadLangConfig") -> bool:
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


def _julia_is_function_node(node, config: "_HalsteadLangConfig") -> bool:
    """Julia: stock function nodes plus short-form assignments."""
    if node.type in config.function_nodes:
        return True
    if node.type == "assignment" and node.children:
        return node.children[0].type == "call_expression"
    return False


# ---------------------------------------------------------------------------
# Per-language configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _HalsteadLangConfig:
    function_nodes: frozenset[str]
    operator_types: frozenset[str]
    operand_types: frozenset[str]
    # Per-language callables. Defaults match the conventional tree-sitter
    # shape; languages whose AST diverges register their own.
    name_extractor: NameExtractor = _default_name_extractor
    is_function_node: FunctionNodeMatcher = _default_is_function_node


_LANG_CONFIG: dict[str, _HalsteadLangConfig] = {
    "python": _HalsteadLangConfig(
        function_nodes=frozenset({"function_definition", "lambda"}),
        operator_types=frozenset({
            "def", "if", "else", "elif", "for", "while", "return",
            "class", "import", "from", "try", "except", "finally",
            "raise", "with", "as", "yield", "lambda", "del", "assert",
            "break", "continue", "pass", "and", "or", "not", "in", "is",
            "=", "+", "-", "*", "/", "**", "//", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "|", "&", "^", "~", "<<", ">>",
            "+=", "-=", "*=", "/=", "//=", "%=", "**=",
            "->", "@",
        }),
        operand_types=frozenset({
            "identifier", "integer", "float", "string",
            "true", "false", "none", "type",
        }),
    ),
    "javascript": _HalsteadLangConfig(
        function_nodes=frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "method_definition",
            "generator_function_declaration",
        }),
        operator_types=frozenset({
            "function", "if", "else", "for", "while", "do", "return",
            "class", "import", "from", "try", "catch", "finally",
            "throw", "new", "delete", "typeof", "instanceof", "void",
            "switch", "case", "default", "break", "continue",
            "var", "let", "const", "yield", "await", "async",
            "=", "+", "-", "*", "/", "%", "**",
            "==", "!=", "===", "!==", "<", ">", "<=", ">=",
            "&&", "||", "??", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=", "**=",
            "++", "--", "=>", "...", "?",
        }),
        operand_types=frozenset({
            "identifier", "property_identifier", "shorthand_property_identifier",
            "number", "string", "string_fragment",
            "template_string", "regex",
            "true", "false", "null", "undefined",
        }),
    ),
    "typescript": _HalsteadLangConfig(
        function_nodes=frozenset({
            "function_declaration", "function_expression",
            "arrow_function", "method_definition",
            "generator_function_declaration",
        }),
        operator_types=frozenset({
            "function", "if", "else", "for", "while", "do", "return",
            "class", "import", "from", "try", "catch", "finally",
            "throw", "new", "delete", "typeof", "instanceof", "void",
            "switch", "case", "default", "break", "continue",
            "var", "let", "const", "yield", "await", "async",
            "interface", "type", "enum", "as",
            "=", "+", "-", "*", "/", "%", "**",
            "==", "!=", "===", "!==", "<", ">", "<=", ">=",
            "&&", "||", "??", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=", "**=",
            "++", "--", "=>", "...", "?",
        }),
        operand_types=frozenset({
            "identifier", "property_identifier", "shorthand_property_identifier",
            "type_identifier",
            "number", "string", "string_fragment",
            "template_string", "regex",
            "true", "false", "null", "undefined",
        }),
    ),
    "go": _HalsteadLangConfig(
        function_nodes=frozenset({
            "function_declaration", "method_declaration", "func_literal",
        }),
        operator_types=frozenset({
            "func", "if", "else", "for", "switch", "case", "default",
            "return", "break", "continue", "go", "defer", "select",
            "range", "type", "struct", "interface", "map", "chan",
            "import", "package", "var", "const",
            "=", ":=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "<-", "...",
        }),
        operand_types=frozenset({
            "identifier", "field_identifier", "type_identifier",
            "package_identifier",
            "int_literal", "float_literal", "imaginary_literal",
            "rune_literal", "raw_string_literal", "interpreted_string_literal",
            "true", "false", "nil", "iota",
        }),
    ),
    "rust": _HalsteadLangConfig(
        function_nodes=frozenset({"function_item", "closure_expression"}),
        operator_types=frozenset({
            "fn", "if", "else", "for", "while", "loop", "match",
            "return", "break", "continue", "let", "mut", "ref",
            "struct", "enum", "impl", "trait", "type", "use", "mod",
            "pub", "self", "super", "crate", "as", "where",
            "async", "await", "unsafe", "move",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "=>", "::", "..", "..=", "?",
        }),
        operand_types=frozenset({
            "identifier", "field_identifier", "type_identifier",
            "integer_literal", "float_literal", "string_literal",
            "raw_string_literal", "char_literal", "boolean_literal",
            "true", "false",
        }),
    ),
    "java": _HalsteadLangConfig(
        function_nodes=frozenset({
            "method_declaration", "constructor_declaration",
            "lambda_expression",
        }),
        operator_types=frozenset({
            "if", "else", "for", "while", "do", "return",
            "class", "interface", "enum", "extends", "implements",
            "import", "package", "try", "catch", "finally",
            "throw", "throws", "new", "instanceof", "switch",
            "case", "default", "break", "continue",
            "public", "private", "protected", "static", "final",
            "abstract", "synchronized", "volatile",
            "void", "super", "this",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>", ">>>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "?", "->",
        }),
        operand_types=frozenset({
            "identifier", "type_identifier", "field_identifier",
            "decimal_integer_literal", "hex_integer_literal",
            "octal_integer_literal", "binary_integer_literal",
            "decimal_floating_point_literal",
            "string_literal", "string_fragment",
            "character_literal",
            "true", "false", "null",
        }),
    ),
    "c_sharp": _HalsteadLangConfig(
        function_nodes=frozenset({
            "method_declaration", "constructor_declaration",
            "lambda_expression",
        }),
        operator_types=frozenset({
            "if", "else", "for", "foreach", "while", "do", "return",
            "class", "struct", "interface", "enum",
            "using", "namespace", "try", "catch", "finally",
            "throw", "new", "is", "as", "switch", "in",
            "case", "default", "break", "continue",
            "public", "private", "protected", "internal", "static",
            "readonly", "abstract", "virtual", "override", "sealed",
            "async", "await", "void", "this", "base", "var",
            "=", "+", "-", "*", "/", "%",
            "==", "!=", "<", ">", "<=", ">=",
            "&&", "||", "!", "~", "&", "|", "^", "<<", ">>",
            "+=", "-=", "*=", "/=", "%=",
            "++", "--", "?", "=>", "??",
        }),
        operand_types=frozenset({
            "identifier", "type_identifier",
            "integer_literal", "real_literal",
            "string_literal", "verbatim_string_literal",
            "interpolated_string_expression",
            "character_literal",
            "true", "false", "null",
        }),
    ),
    "julia": _HalsteadLangConfig(
        function_nodes=frozenset({
            "function_definition",
            "arrow_function_expression",
            "do_clause",       # `map(xs) do x ... end` body
        }),
        operator_types=frozenset({
            # Keywords
            "function", "return", "if", "else", "elseif", "end",
            "for", "while", "break", "continue", "in",
            "try", "catch", "finally", "throw",
            "do", "begin", "let", "global", "local",
            "module", "using", "import", "export",
            "struct", "mutable", "abstract", "primitive", "type",
            "const",
            # Operators (tree-sitter-julia exposes these as "operator" nodes
            # rather than literal token types; the kernel reads operator
            # symbols from the operator child's text where applicable. We
            # list the bare token strings here so generic walk-and-match
            # logic still finds them.)
            "=", "+", "-", "*", "/", "%", "^", "//", ".",
            "==", "!=", "<", ">", "<=", ">=", "===", "!==",
            "&&", "||", "!", "&", "|", "<<", ">>",
            "+=", "-=", "*=", "/=",
            "->", "::", ":", "?", "@", "...",
        }),
        operand_types=frozenset({
            "identifier", "integer_literal", "float_literal",
            "string_literal", "character_literal",
            "true", "false", "nothing", "missing",
        }),
        name_extractor=_julia_name_extractor,
        is_function_node=_julia_is_function_node,
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
}


# ---------------------------------------------------------------------------
# AST helpers
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


def _extract_function_name(node, content: bytes, config: _HalsteadLangConfig) -> str:
    """Delegate to the per-language ``name_extractor`` callable on ``config``."""
    return config.name_extractor(node, content)


# ---------------------------------------------------------------------------
# Token classification + metric computation
# ---------------------------------------------------------------------------


def _collect_tokens(
    node, content: bytes, config: _HalsteadLangConfig,
) -> tuple[set[str], set[str], int, int]:
    """Walk a subtree and collect operator/operand tokens.

    Returns (unique_operators, unique_operands, total_operators, total_operands).
    Stops at nested function definitions.
    """
    operators: set[str] = set()
    operands: set[str] = set()
    total_ops = 0
    total_opnds = 0

    def walk(n):
        nonlocal total_ops, total_opnds
        # Don't descend into nested functions
        if config.is_function_node(n, config) and n is not node:
            return
        if n.child_count == 0:
            # Leaf node — classify
            ntype = n.type
            if ntype in config.operator_types:
                text = _node_text(n, content)
                operators.add(text)
                total_ops += 1
            elif ntype in config.operand_types:
                text = _node_text(n, content)
                operands.add(text)
                total_opnds += 1
            # else: ignored (punctuation, etc.)
        for child in n.children:
            walk(child)

    walk(node)
    return operators, operands, total_ops, total_opnds


def _compute_halstead(
    n1: int, n2: int, total_n1: int, total_n2: int,
) -> tuple[int, int, float, float, float]:
    """Compute derived Halstead metrics from raw counts."""
    vocabulary = n1 + n2
    length = total_n1 + total_n2
    volume = length * math.log2(vocabulary) if vocabulary > 0 else 0.0
    difficulty = (n1 / 2) * (total_n2 / n2) if n2 > 0 else 0.0
    effort = difficulty * volume
    return vocabulary, length, volume, difficulty, effort


# ---------------------------------------------------------------------------
# Main kernel
# ---------------------------------------------------------------------------


def halstead_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
    min_volume: float = 0,
) -> HalsteadResult:
    """Compute Halstead Software Science metrics per function."""
    errors: list[str] = []

    if languages:
        active = {l.lower() for l in languages} & set(_LANG_CONFIG)
    else:
        active = set(_LANG_CONFIG)
    if not active:
        return HalsteadResult(
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

    all_functions: list[HalsteadMetrics] = []
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
                body = node.child_by_field_name("body") or node

                ops, opnds, total_ops, total_opnds = _collect_tokens(
                    body, content, config,
                )

                n1, n2 = len(ops), len(opnds)
                if n1 == 0 and n2 == 0:
                    return  # empty function

                vocab, length, volume, difficulty, effort = _compute_halstead(
                    n1, n2, total_ops, total_opnds,
                )

                if volume >= min_volume:
                    all_functions.append(HalsteadMetrics(
                        name=name, file=rel, path=str(fp),
                        line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        language=lang,
                        n1=n1, n2=n2,
                        total_n1=total_ops, total_n2=total_opnds,
                        vocabulary=vocab, length=length,
                        volume=round(volume, 2),
                        difficulty=round(difficulty, 2),
                        effort=round(effort, 2),
                    ))
                    language_counts[lang] = language_counts.get(lang, 0) + 1
                return  # don't descend into nested functions
            for child in node.children:
                find_functions(child)

        find_functions(tree.root_node)

    all_functions.sort(key=lambda f: (-f.volume, f.file, f.line))

    truncated = False
    if max_results is not None and len(all_functions) > max_results:
        all_functions = all_functions[:max_results]
        truncated = True

    return HalsteadResult(
        functions=all_functions,
        files_searched=find_result.total_found,
        functions_analyzed=len(all_functions),
        languages=language_counts,
        errors=errors,
        truncated=truncated,
    )
