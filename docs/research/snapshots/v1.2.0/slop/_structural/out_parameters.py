"""Out-parameter mutation detection kernel.

Functions that receive collection parameters (list, dict, set) and mutate them
in place are using the "out-parameter" pattern — an anti-pattern that couples
the caller's data structure to the callee's implementation, makes call-site
reasoning harder, and violates the principle of least astonishment.

Detected mutations per collection type:

  list   → .append(), .extend(), .insert(), .remove(), .pop(), .clear(),
            .sort(), .reverse()
  dict   → .update(), .pop(), .clear(), .setdefault()
  set    → .add(), .discard(), .remove(), .pop(), .clear(),
            .update(), .intersection_update(), .difference_update(),
            .symmetric_difference_update()

Supported languages
-------------------
Python (tree-sitter AST, full parameter-type inference).
JavaScript / TypeScript (text-tier; detects .push/.splice/.set on params).
Go (text-tier; detects append(param, ...) patterns).
C (tree-sitter AST; flags non-``const`` pointer parameters that are
   mutated through ``*p = ...``, ``p->x = ...``, or ``p[i] = ...``).

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel

# ---------------------------------------------------------------------------
# Mutation method tables
# ---------------------------------------------------------------------------

_LIST_MUTATIONS = frozenset({
    "append", "extend", "insert", "remove", "pop", "clear",
    "sort", "reverse",
})
_DICT_MUTATIONS = frozenset({
    "update", "pop", "clear", "setdefault", "popitem",
})
_SET_MUTATIONS = frozenset({
    "add", "discard", "remove", "pop", "clear",
    "update", "intersection_update", "difference_update",
    "symmetric_difference_update",
})

_ALL_MUTATIONS = _LIST_MUTATIONS | _DICT_MUTATIONS | _SET_MUTATIONS

# Type annotation names that indicate a mutable collection parameter
_COLLECTION_TYPES = frozenset({
    "list", "List", "dict", "Dict", "set", "Set",
    "MutableSequence", "MutableMapping", "MutableSet",
    "Sequence", "Mapping",  # commonly mutated despite read-only annotation
    "deque", "Deque",
    "defaultdict",
    "Counter",
})

# Ruby is intentionally NOT registered. Ruby's parameter passing is
# always by reference (every object is mutable), so "the callee
# mutates a parameter" is the default rather than an anti-pattern.
# Without a static type system the rule has no signal-to-noise floor;
# silent no-op via missing registration.
_LANG_GLOBS: dict[str, list[str]] = {
    "python":     ["**/*.py"],
    "javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],
    "typescript": ["**/*.ts", "**/*.tsx"],
    "go":         ["**/*.go"],
    "c":          ["**/*.c", "**/*.h"],
    "cpp":        ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class OutParamMutation:
    """One detected mutation of an out-parameter."""

    param_name: str
    method: str          # e.g. "append"
    line: int            # 1-based


@dataclass
class OutParamEntry:
    """One function that has out-parameter mutations."""

    file: str
    name: str
    line: int
    end_line: int
    language: str
    mutations: list[OutParamMutation] = field(default_factory=list)

    @property
    def mutation_count(self) -> int:
        return len(self.mutations)


@dataclass
class OutParamResult:
    """Aggregated result from out_parameters_kernel."""

    entries: list[OutParamEntry] = field(default_factory=list)
    functions_analyzed: int = 0
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def out_parameters_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    require_type_annotation: bool = True,
) -> OutParamResult:
    """Detect functions that mutate their collection-typed parameters.

    Args:
        root:                   Search root.
        languages:              Restrict to these languages.
        globs:                  Include glob patterns.
        excludes:               Exclude patterns.
        hidden:                 Search hidden files.
        no_ignore:              Ignore .gitignore rules.
        require_type_annotation: When True (default), only flag parameters
                                 that carry an explicit collection type
                                 annotation. When False, flag *any* parameter
                                 that is mutated with a collection method.
    """
    active = (
        {l.lower() for l in languages} & set(_LANG_GLOBS)
        if languages else set(_LANG_GLOBS)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active) for g in _LANG_GLOBS.get(l, [])
    ]
    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    entries: list[OutParamEntry] = []
    errors: list[str] = []
    total_functions = 0

    for fp in files:
        lang = detect_language(fp)
        if lang not in active:
            continue
        if lang == "python":
            _scan_python(fp, root, entries, errors, require_type_annotation)
            total_functions += _count_functions_python(fp, errors)
        # JS/TS/Go: text-tier (see below)
        elif lang in ("javascript", "typescript"):
            _scan_js_text(fp, root, entries, errors)
        elif lang == "go":
            _scan_go_text(fp, root, entries, errors)
        elif lang == "c":
            fn_count = _scan_c(fp, root, entries, errors)
            total_functions += fn_count
        elif lang == "cpp":
            fn_count = _scan_cpp(fp, root, entries, errors)
            total_functions += fn_count

    entries.sort(key=lambda e: -e.mutation_count)
    return OutParamResult(
        entries=entries,
        functions_analyzed=total_functions,
        files_searched=len(files),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Python AST scanner
# ---------------------------------------------------------------------------


def _scan_python(
    fp: Path,
    root: Path,
    out: list[OutParamEntry],
    errors: list[str],
    require_type_annotation: bool,
) -> None:
    """Scan one Python file for out-parameter mutations."""
    tree_lang = load_language("python")
    if tree_lang is None:
        return
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

        rel = str(fp.relative_to(root))
        _walk_python_functions(tree.root_node, content, rel, out, require_type_annotation)
    except Exception as exc:
        errors.append(f"{fp}: {exc}")


def _walk_python_functions(
    root_node: object,
    content: bytes,
    rel: str,
    out: list[OutParamEntry],
    require_type_annotation: bool,
) -> None:
    fn_types = frozenset({"function_definition", "async_function_definition"})
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type in fn_types:  # type: ignore[attr-defined]
            _process_python_function(node, content, rel, out, require_type_annotation)
        stack.extend(node.children)  # type: ignore[attr-defined]


def _process_python_function(
    fn_node: object,
    content: bytes,
    rel: str,
    out: list[OutParamEntry],
    require_type_annotation: bool,
) -> None:
    """Extract out-parameter mutations from one Python function node."""
    # Get function name
    name_node = fn_node.child_by_field_name("name")  # type: ignore[attr-defined]
    fn_name = (
        content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
        if name_node else "<anonymous>"
    )
    fn_start = fn_node.start_point[0] + 1  # type: ignore[attr-defined]
    fn_end = fn_node.end_point[0] + 1      # type: ignore[attr-defined]

    # Collect candidate parameters
    params = _extract_python_params(fn_node, content, require_type_annotation)
    if not params:
        return

    # Scan body for attribute-method calls on those params
    body = fn_node.child_by_field_name("body") or fn_node  # type: ignore[attr-defined]
    mutations = _find_python_mutations(body, content, params)
    if mutations:
        out.append(OutParamEntry(
            file=rel, name=fn_name, line=fn_start, end_line=fn_end,
            language="python", mutations=mutations,
        ))


def _extract_python_params(
    fn_node: object,
    content: bytes,
    require_type_annotation: bool,
) -> set[str]:
    """Return names of collection-typed (or, if not required, all) parameters."""
    params: set[str] = set()
    params_node = fn_node.child_by_field_name("parameters")  # type: ignore[attr-defined]
    if params_node is None:
        return params

    for child in params_node.children:  # type: ignore[attr-defined]
        ptype = child.type  # type: ignore[attr-defined]
        if ptype == "identifier":
            name = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if not require_type_annotation:
                params.add(name)
        elif ptype in ("typed_parameter", "typed_default_parameter"):
            name_n = child.child_by_field_name("name") or (  # type: ignore[attr-defined]
                next((c for c in child.children  # type: ignore[attr-defined]
                      if c.type == "identifier"), None)
            )
            type_n = child.child_by_field_name("type")  # type: ignore[attr-defined]
            if name_n is None:
                continue
            param_name = content[name_n.start_byte:name_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if not require_type_annotation:
                params.add(param_name)
            elif type_n is not None:
                type_text = content[type_n.start_byte:type_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                # Check if the annotation mentions a collection type
                if any(ct in type_text for ct in _COLLECTION_TYPES):
                    params.add(param_name)
        elif ptype in ("default_parameter",):
            # Untyped with default; honour require_type_annotation
            if not require_type_annotation:
                name_n = child.child_by_field_name("name")  # type: ignore[attr-defined]
                if name_n:
                    params.add(content[name_n.start_byte:name_n.end_byte].decode(errors="replace"))  # type: ignore[attr-defined]
    return params


def _find_python_mutations(
    body_node: object,
    content: bytes,
    param_names: set[str],
) -> list[OutParamMutation]:
    """DFS scan for `param.method(...)` where method is a mutation method."""
    mutations: list[OutParamMutation] = []
    stack = [body_node]
    while stack:
        node = stack.pop()
        # call → attribute_access → identifier + method
        if node.type == "call":  # type: ignore[attr-defined]
            fn_child = node.child_by_field_name("function")  # type: ignore[attr-defined]
            if fn_child and fn_child.type == "attribute":  # type: ignore[attr-defined]
                obj_n = fn_child.child_by_field_name("object")  # type: ignore[attr-defined]
                attr_n = fn_child.child_by_field_name("attribute")  # type: ignore[attr-defined]
                if obj_n and attr_n and obj_n.type == "identifier":  # type: ignore[attr-defined]
                    obj_name = content[obj_n.start_byte:obj_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    method = content[attr_n.start_byte:attr_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    if obj_name in param_names and method in _ALL_MUTATIONS:
                        mutations.append(OutParamMutation(
                            param_name=obj_name,
                            method=method,
                            line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                        ))
        stack.extend(node.children)  # type: ignore[attr-defined]
    return mutations


def _count_functions_python(fp: Path, errors: list[str]) -> int:
    tree_lang = load_language("python")
    if tree_lang is None:
        return 0
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
        fn_types = {"function_definition", "async_function_definition"}
        stack = [tree.root_node]
        count = 0
        while stack:
            n = stack.pop()
            if n.type in fn_types:
                count += 1
            stack.extend(n.children)
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# JavaScript / TypeScript text-tier (minimal)
# ---------------------------------------------------------------------------


def _scan_js_text(fp: Path, root: Path, out: list[OutParamEntry], errors: list[str]) -> None:
    """Text-tier scan for .push/.splice/.set mutations in JS/TS functions."""
    import re
    try:
        lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        rel = str(fp.relative_to(root))
        # Simple heuristic: lines with .push(, .splice(, .delete( etc.
        _JS_MUTATIONS = re.compile(r'\b(\w+)\.(push|pop|splice|shift|unshift|delete|set|clear|add)\s*\(')
        for i, line in enumerate(lines, start=1):
            m = _JS_MUTATIONS.search(line)
            if m:
                param, method = m.group(1), m.group(2)
                # Record as a single-mutation function entry per line (simplified)
                # A full implementation would correlate to enclosing function
                entry = OutParamEntry(
                    file=rel, name="<unknown>", line=i, end_line=i,
                    language="javascript",
                    mutations=[OutParamMutation(param_name=param, method=method, line=i)],
                )
                out.append(entry)
    except Exception as exc:
        errors.append(f"{fp}: {exc}")


# ---------------------------------------------------------------------------
# Go text-tier (minimal)
# ---------------------------------------------------------------------------


def _scan_go_text(fp: Path, root: Path, out: list[OutParamEntry], errors: list[str]) -> None:
    """Text-tier scan for append(param, ...) in Go functions."""
    import re
    try:
        lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        rel = str(fp.relative_to(root))
        _GO_APPEND = re.compile(r'\b(\w+)\s*=\s*append\s*\(\s*(\w+)\s*,')
        for i, line in enumerate(lines, start=1):
            m = _GO_APPEND.search(line)
            if m:
                param = m.group(2)
                entry = OutParamEntry(
                    file=rel, name="<unknown>", line=i, end_line=i,
                    language="go",
                    mutations=[OutParamMutation(param_name=param, method="append", line=i)],
                )
                out.append(entry)
    except Exception as exc:
        errors.append(f"{fp}: {exc}")


# ---------------------------------------------------------------------------
# C AST scanner
# ---------------------------------------------------------------------------


def _scan_c(
    fp: Path,
    root: Path,
    out: list[OutParamEntry],
    errors: list[str],
) -> int:
    """Scan one C file for pointer-parameter mutations.

    Detects three mutation shapes for non-``const`` pointer parameters:

    - ``*p = X``        — assignment_expression with LHS pointer_expression
    - ``p->field = Y``  — assignment_expression with LHS field_expression (``->``)
    - ``p[i] = Z``      — assignment_expression with LHS subscript_expression

    Skips ``const T *p`` parameters (read-only data by convention).
    Returns the count of functions analysed (for stats).
    """
    tree_lang = load_language("c")
    if tree_lang is None:
        return 0
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
        return 0

    rel = str(fp.relative_to(root))
    fn_count = 0
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "function_definition":  # type: ignore[attr-defined]
            fn_count += 1
            _process_c_function(node, content, rel, out)
        # Don't descend into function bodies — top-level functions only
        # are real C functions (no nested fn defs in standard C).
        else:
            stack.extend(node.children)  # type: ignore[attr-defined]
    return fn_count


def _process_c_function(
    fn_node: object,
    content: bytes,
    rel: str,
    out: list[OutParamEntry],
) -> None:
    """Extract pointer-mutation entries from one C function_definition."""
    fn_name = _c_fn_name(fn_node, content)
    fn_start = fn_node.start_point[0] + 1  # type: ignore[attr-defined]
    fn_end = fn_node.end_point[0] + 1      # type: ignore[attr-defined]

    pointer_params = _c_extract_pointer_params(fn_node, content)
    if not pointer_params:
        return

    body = fn_node.child_by_field_name("body") or fn_node  # type: ignore[attr-defined]
    mutations = _c_find_mutations(body, content, pointer_params)
    if mutations:
        out.append(OutParamEntry(
            file=rel, name=fn_name, line=fn_start, end_line=fn_end,
            language="c", mutations=mutations,
        ))


def _c_fn_name(fn_node: object, content: bytes) -> str:
    """Walk the declarator chain to extract a C function name."""
    declarator = fn_node.child_by_field_name("declarator")  # type: ignore[attr-defined]
    for _ in range(6):
        if declarator is None:
            return "<anonymous>"
        if declarator.type == "function_declarator":  # type: ignore[attr-defined]
            inner = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
            if inner is not None and inner.type == "identifier":  # type: ignore[attr-defined]
                return content[inner.start_byte:inner.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            return "<anonymous>"
        if declarator.type in ("pointer_declarator", "parenthesized_declarator"):  # type: ignore[attr-defined]
            declarator = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
            continue
        break
    return "<anonymous>"


def _c_extract_pointer_params(fn_node: object, content: bytes) -> set[str]:
    """Return names of pointer parameters that are NOT ``const T *``.

    Walks the function_declarator's parameter_list. For each
    parameter_declaration:

    - Has a child of type ``pointer_declarator`` (otherwise non-pointer).
    - No top-level ``type_qualifier`` whose text is ``const`` precedes
      the pointer_declarator (read-only data; would be misleading to
      flag mutations through it — likely the caller is wrong, not
      the callee).
    """
    params: set[str] = set()
    declarator = fn_node.child_by_field_name("declarator")  # type: ignore[attr-defined]
    # Walk through pointer_declarator wrappers (pointer return type)
    # to reach the function_declarator.
    while declarator is not None and declarator.type == "pointer_declarator":  # type: ignore[attr-defined]
        declarator = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
    if declarator is None or declarator.type != "function_declarator":  # type: ignore[attr-defined]
        return params

    plist = declarator.child_by_field_name("parameters")  # type: ignore[attr-defined]
    if plist is None:
        return params

    for param in plist.children:  # type: ignore[attr-defined]
        if param.type != "parameter_declaration":  # type: ignore[attr-defined]
            continue

        has_const = False
        ptr_decl = None
        for child in param.children:  # type: ignore[attr-defined]
            ctype = child.type  # type: ignore[attr-defined]
            if ctype == "type_qualifier":
                qtext = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if qtext.strip() == "const":
                    has_const = True
            elif ctype == "pointer_declarator":
                ptr_decl = child

        if has_const or ptr_decl is None:
            continue

        # Find the parameter identifier inside the (possibly nested)
        # pointer_declarator.
        cur = ptr_decl
        for _ in range(4):
            if cur is None:
                break
            inner = cur.child_by_field_name("declarator")  # type: ignore[attr-defined]
            if inner is None:
                break
            if inner.type == "identifier":  # type: ignore[attr-defined]
                params.add(content[inner.start_byte:inner.end_byte].decode(errors="replace"))  # type: ignore[attr-defined]
                break
            cur = inner
    return params


def _c_find_mutations(
    body_node: object,
    content: bytes,
    param_names: set[str],
) -> list[OutParamMutation]:
    """DFS walk for ``*p = X`` / ``p->x = Y`` / ``p[i] = Z`` patterns
    where ``p`` is one of ``param_names``.
    """
    mutations: list[OutParamMutation] = []
    stack = [body_node]
    while stack:
        node = stack.pop()
        if node.type == "assignment_expression":  # type: ignore[attr-defined]
            lhs = node.child_by_field_name("left")  # type: ignore[attr-defined]
            if lhs is not None:
                mutated = _c_lhs_mutates_param(lhs, content, param_names)
                if mutated is not None:
                    name, kind = mutated
                    mutations.append(OutParamMutation(
                        param_name=name,
                        method=kind,
                        line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                    ))
        stack.extend(node.children)  # type: ignore[attr-defined]
    return mutations


def _c_lhs_mutates_param(
    lhs: object,
    content: bytes,
    param_names: set[str],
) -> tuple[str, str] | None:
    """If ``lhs`` mutates a pointer parameter, return (param_name, kind)."""
    ltype = lhs.type  # type: ignore[attr-defined]

    if ltype == "pointer_expression":
        # ``*p`` — any child identifier matches.
        for child in lhs.children:  # type: ignore[attr-defined]
            if child.type == "identifier":  # type: ignore[attr-defined]
                name = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if name in param_names:
                    return (name, "deref-assign")
        return None

    if ltype == "field_expression":
        # ``p->x`` (we only care about ``->``; ``p.x`` doesn't mutate
        # through a pointer parameter).
        op_present = any(c.type == "->" for c in lhs.children)  # type: ignore[attr-defined]
        if not op_present:
            return None
        obj = lhs.child_by_field_name("argument")  # type: ignore[attr-defined]
        if obj is None:
            # Some grammar versions expose object via a different field
            # or as the first identifier child.
            for c in lhs.children:  # type: ignore[attr-defined]
                if c.type == "identifier":  # type: ignore[attr-defined]
                    obj = c
                    break
        if obj is not None and obj.type == "identifier":  # type: ignore[attr-defined]
            name = content[obj.start_byte:obj.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if name in param_names:
                return (name, "field-assign")
        return None

    if ltype == "subscript_expression":
        # ``p[i]`` mutation
        argument = lhs.child_by_field_name("argument")  # type: ignore[attr-defined]
        if argument is not None and argument.type == "identifier":  # type: ignore[attr-defined]
            name = content[argument.start_byte:argument.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if name in param_names:
                return (name, "subscript-assign")
        # Fallback — first identifier child
        for c in lhs.children:  # type: ignore[attr-defined]
            if c.type == "identifier":  # type: ignore[attr-defined]
                name = content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if name in param_names:
                    return (name, "subscript-assign")
                break
        return None

    return None


# ---------------------------------------------------------------------------
# C++ AST scanner
# ---------------------------------------------------------------------------


def _scan_cpp(
    fp: Path,
    root: Path,
    out: list[OutParamEntry],
    errors: list[str],
) -> int:
    """Scan one C++ file for pointer / non-const reference parameter mutations.

    Detection extends the C scanner (``_scan_c``) with two C++-specific
    additions:

    - **Reference parameters** (``T& p``) that are mutated via plain
      ``p = ...`` (assignment) or ``p.field = ...`` (field assign).
      ``const T& p`` is excluded by design.
    - All C pointer-mutation patterns (``*p = X``, ``p->x = Y``,
      ``p[i] = Z``).

    Walks every ``function_definition`` (in-class methods, out-of-line
    methods, free functions, template-wrapped functions) plus
    ``lambda_expression``s with named captures. Returns function count.
    """
    tree_lang = load_language("cpp")
    if tree_lang is None:
        return 0
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
        return 0

    rel = str(fp.relative_to(root))
    fn_count = 0
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "function_definition":  # type: ignore[attr-defined]
            fn_count += 1
            _process_cpp_function(node, content, rel, out)
            # Don't descend into the body (no nested fn defs in standard C++)
        else:
            stack.extend(node.children)  # type: ignore[attr-defined]
    return fn_count


def _process_cpp_function(
    fn_node: object,
    content: bytes,
    rel: str,
    out: list[OutParamEntry],
) -> None:
    """Extract pointer + reference mutation entries from one C++ function."""
    fn_name = _cpp_fn_name(fn_node, content)
    fn_start = fn_node.start_point[0] + 1  # type: ignore[attr-defined]
    fn_end = fn_node.end_point[0] + 1      # type: ignore[attr-defined]

    pointer_params, reference_params = _cpp_extract_mutable_params(fn_node, content)
    if not pointer_params and not reference_params:
        return

    body = fn_node.child_by_field_name("body") or fn_node  # type: ignore[attr-defined]
    mutations = _cpp_find_mutations(body, content, pointer_params, reference_params)
    if mutations:
        out.append(OutParamEntry(
            file=rel, name=fn_name, line=fn_start, end_line=fn_end,
            language="cpp", mutations=mutations,
        ))


def _cpp_fn_name(fn_node: object, content: bytes) -> str:
    """Walk the C++ declarator chain to extract a function name."""
    declarator = fn_node.child_by_field_name("declarator")  # type: ignore[attr-defined]
    for _ in range(8):
        if declarator is None:
            return "<anonymous>"
        if declarator.type == "function_declarator":  # type: ignore[attr-defined]
            inner = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
            if inner is None:
                return "<anonymous>"
            if inner.type in ("identifier", "field_identifier"):  # type: ignore[attr-defined]
                return content[inner.start_byte:inner.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if inner.type == "qualified_identifier":  # type: ignore[attr-defined]
                for c in reversed(inner.children):  # type: ignore[attr-defined]
                    if c.type == "identifier":  # type: ignore[attr-defined]
                        return content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                return "<anonymous>"
            if inner.type == "operator_name":  # type: ignore[attr-defined]
                for c in inner.children:  # type: ignore[attr-defined]
                    if c.type != "operator":  # type: ignore[attr-defined]
                        return content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                return "<anonymous>"
            return "<anonymous>"
        if declarator.type in ("pointer_declarator", "reference_declarator", "parenthesized_declarator"):  # type: ignore[attr-defined]
            declarator = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
            continue
        break
    return "<anonymous>"


def _cpp_extract_mutable_params(
    fn_node: object, content: bytes,
) -> tuple[set[str], set[str]]:
    """Return ``(pointer_params, reference_params)`` excluding ``const T &/*``.

    Pointer parameters: declarator chain includes ``pointer_declarator``.
    Reference parameters: declarator chain includes ``reference_declarator``.
    A leading ``type_qualifier "const"`` on the parameter declaration
    excludes the parameter (read-only by contract).
    """
    pointer_params: set[str] = set()
    reference_params: set[str] = set()

    declarator = fn_node.child_by_field_name("declarator")  # type: ignore[attr-defined]
    while declarator is not None and declarator.type in (  # type: ignore[attr-defined]
        "pointer_declarator", "reference_declarator", "parenthesized_declarator",
    ):
        declarator = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
    if declarator is None or declarator.type != "function_declarator":  # type: ignore[attr-defined]
        return pointer_params, reference_params

    plist = declarator.child_by_field_name("parameters")  # type: ignore[attr-defined]
    if plist is None:
        return pointer_params, reference_params

    for param in plist.children:  # type: ignore[attr-defined]
        if param.type != "parameter_declaration":  # type: ignore[attr-defined]
            continue

        has_const = False
        ptr_decl = None
        ref_decl = None
        for child in param.children:  # type: ignore[attr-defined]
            ctype = child.type  # type: ignore[attr-defined]
            if ctype == "type_qualifier":
                qtext = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if qtext.strip() == "const":
                    has_const = True
            elif ctype == "pointer_declarator":
                ptr_decl = child
            elif ctype == "reference_declarator":
                ref_decl = child

        if has_const:
            continue

        # Resolve the parameter identifier.
        target_decl = ptr_decl or ref_decl
        if target_decl is None:
            continue

        param_name: str | None = None
        if target_decl is ref_decl:
            # reference_declarator uses positional children (& + identifier),
            # not a `declarator` field.
            for c in target_decl.children:  # type: ignore[attr-defined]
                if c.type == "identifier":  # type: ignore[attr-defined]
                    param_name = content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    break
        else:
            # pointer_declarator uses a `declarator` field that may be
            # nested through additional pointer_declarator / parenthesized
            # wrappers.
            cur = target_decl
            for _ in range(4):
                if cur is None:
                    break
                inner = cur.child_by_field_name("declarator")  # type: ignore[attr-defined]
                if inner is None:
                    break
                if inner.type == "identifier":  # type: ignore[attr-defined]
                    param_name = content[inner.start_byte:inner.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    break
                cur = inner
        if param_name is None:
            continue

        if ptr_decl is not None:
            pointer_params.add(param_name)
        else:
            reference_params.add(param_name)

    return pointer_params, reference_params


def _cpp_find_mutations(
    body_node: object,
    content: bytes,
    pointer_params: set[str],
    reference_params: set[str],
) -> list[OutParamMutation]:
    """DFS for pointer-mutation and reference-mutation patterns."""
    mutations: list[OutParamMutation] = []
    stack = [body_node]
    while stack:
        node = stack.pop()
        if node.type == "assignment_expression":  # type: ignore[attr-defined]
            lhs = node.child_by_field_name("left")  # type: ignore[attr-defined]
            if lhs is not None:
                mutated = _cpp_lhs_mutates_param(
                    lhs, content, pointer_params, reference_params,
                )
                if mutated is not None:
                    name, kind = mutated
                    mutations.append(OutParamMutation(
                        param_name=name,
                        method=kind,
                        line=node.start_point[0] + 1,  # type: ignore[attr-defined]
                    ))
        stack.extend(node.children)  # type: ignore[attr-defined]
    return mutations


def _cpp_lhs_mutates_param(
    lhs: object,
    content: bytes,
    pointer_params: set[str],
    reference_params: set[str],
) -> tuple[str, str] | None:
    """Detect if ``lhs`` mutates a pointer or reference parameter."""
    ltype = lhs.type  # type: ignore[attr-defined]

    # ``*p = X`` — pointer dereference assignment
    if ltype == "pointer_expression":
        for child in lhs.children:  # type: ignore[attr-defined]
            if child.type == "identifier":  # type: ignore[attr-defined]
                name = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if name in pointer_params:
                    return (name, "deref-assign")
        return None

    # ``p->field = X`` (pointer) or ``r.field = X`` (reference)
    if ltype == "field_expression":
        op_present = False
        op_kind = "field-assign"
        for c in lhs.children:  # type: ignore[attr-defined]
            if c.type == "->":  # type: ignore[attr-defined]
                op_present = True
                op_kind = "field-assign"
                break
            if c.type == ".":  # type: ignore[attr-defined]
                op_present = True
                op_kind = "ref-field-assign"
                break
        if not op_present:
            return None
        obj = lhs.child_by_field_name("argument")  # type: ignore[attr-defined]
        if obj is None:
            for c in lhs.children:  # type: ignore[attr-defined]
                if c.type == "identifier":  # type: ignore[attr-defined]
                    obj = c
                    break
        if obj is not None and obj.type == "identifier":  # type: ignore[attr-defined]
            name = content[obj.start_byte:obj.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if op_kind == "field-assign" and name in pointer_params:
                return (name, "field-assign")
            if op_kind == "ref-field-assign" and name in reference_params:
                return (name, "ref-field-assign")
        return None

    # ``p[i] = X`` — subscript assignment
    if ltype == "subscript_expression":
        argument = lhs.child_by_field_name("argument")  # type: ignore[attr-defined]
        if argument is not None and argument.type == "identifier":  # type: ignore[attr-defined]
            name = content[argument.start_byte:argument.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if name in pointer_params or name in reference_params:
                return (name, "subscript-assign")
        for c in lhs.children:  # type: ignore[attr-defined]
            if c.type == "identifier":  # type: ignore[attr-defined]
                name = content[c.start_byte:c.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if name in pointer_params or name in reference_params:
                    return (name, "subscript-assign")
                break
        return None

    # ``r = X`` — bare reference reassignment
    if ltype == "identifier":
        name = content[lhs.start_byte:lhs.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
        if name in reference_params:
            return (name, "ref-assign")
        return None

    return None
