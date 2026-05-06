"""Scope-stutter detection kernel.

Identifies identifiers that repeat tokens from their enclosing scope (function,
class, or module). This is a common agentic naming smell where context is
redundantly baked into variable names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel
from slop._lexical.identifier_tokens import split_identifier

# Node types for scopes
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
        "class": frozenset({"type_declaration"}), # Go 'types' often act as classes
    },
    "rust": {
        "function": frozenset({"function_item"}),
        "class": frozenset({"struct_item", "enum_item", "impl_item"}),
    },
    "c": {
        "function": frozenset({"function_definition"}),
        # C has no class concept; structs do not own scope. Empty set
        # disables class-scope stutter checks for .c/.h files.
        "class": frozenset(),
    },
    "cpp": {
        "function": frozenset({"function_definition", "lambda_expression"}),
        # C++ scopes that own identifier vocabulary: classes, structs
        # (which can have methods in C++), and namespaces.
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

@dataclass
class StutterViolation:
    identifier: str
    tokens: list[str]
    scope_name: str
    scope_type: str # 'function', 'class', 'module'
    overlap: list[str]
    line: int
    column: int

@dataclass
class FunctionStutters:
    name: str
    file: str
    line: int
    end_line: int
    language: str
    violations: list[StutterViolation] = field(default_factory=list)

@dataclass
class StutterResult:
    functions: list[FunctionStutters] = field(default_factory=list)
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)

def stutter_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    excludes: list[str] | None = None,
) -> StutterResult:
    active = ({l.lower() for l in languages} & set(_SCOPE_NODES)) if languages else set(_SCOPE_NODES)
    find_globs = [g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])]

    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    results: list[FunctionStutters] = []
    errors: list[str] = []

    for fp in files:
        lang = detect_language(fp)
        if lang not in active: continue

        tree_lang = load_language(lang)
        if tree_lang is None: continue

        try:
            import tree_sitter
            content = fp.read_bytes()
            parser = tree_sitter.Parser()
            parser.language = tree_lang
            tree = parser.parse(content)

            rel = str(fp.relative_to(root))
            module_name = fp.stem
            _scan_file(tree.root_node, content, rel, lang, module_name, results)
        except Exception as exc:
            errors.append(f"{fp}: {exc}")

    return StutterResult(functions=results, files_searched=len(files), errors=errors)

def _scan_file(root_node, content, rel, lang, module_name, out):
    module_tokens = set(split_identifier(module_name))
    # Stack stores (node, scope_stack)
    # scope_stack is a list of (name, type, tokens)
    stack = [(root_node, [ (module_name, 'module', module_tokens) ])]

    fn_nodes = _SCOPE_NODES[lang]["function"]
    class_nodes = _SCOPE_NODES[lang]["class"]

    while stack:
        node, scope_stack = stack.pop()

        next_scope_stack = scope_stack

        if node.type in fn_nodes:
            name = _get_name(node, content)
            tokens = set(split_identifier(name))
            next_scope_stack = scope_stack + [(name, 'function', tokens)]

            # Process function body for stutters
            violations = _process_function_body(node, content, next_scope_stack)
            if violations:
                out.append(FunctionStutters(
                    name=name,
                    file=rel,
                    line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    language=lang,
                    violations=violations
                ))
        elif node.type in class_nodes:
            name = _get_name(node, content)
            tokens = set(split_identifier(name))
            next_scope_stack = scope_stack + [(name, 'class', tokens)]

        for child in reversed(node.children):
            stack.append((child, next_scope_stack))

def _process_function_body(fn_node, content, scope_stack) -> list[StutterViolation]:
    body = fn_node.child_by_field_name("body") or fn_node
    identifiers = []
    _collect_identifier_nodes(body, identifiers)

    violations = []
    for ident_node in identifiers:
        name = content[ident_node.start_byte:ident_node.end_byte].decode(errors="replace")
        if name.startswith("_") and not name.startswith("__"): continue # Skip internal-looking locals

        tokens = split_identifier(name)
        if not tokens: continue

        token_set = set(tokens)

        # Check against all scopes in stack (module, class, function)
        for scope_name, scope_type, scope_tokens in reversed(scope_stack):
            # If we're checking a function's local variables against THAT function's name,
            # that's a stutter.
            overlap = token_set & scope_tokens
            if len(overlap) >= 2:
                violations.append(StutterViolation(
                    identifier=name,
                    tokens=tokens,
                    scope_name=scope_name,
                    scope_type=scope_type,
                    overlap=sorted(list(overlap)),
                    line=ident_node.start_point[0] + 1,
                    column=ident_node.start_point[1]
                ))
                break # Only report most immediate scope overlap
    return violations

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
    # Ruby method / singleton_method: name lives positionally.
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
    # C / C++ ``function_definition`` walks the declarator chain.
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
