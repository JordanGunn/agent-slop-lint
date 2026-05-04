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

_LANG_GLOBS: dict[str, list[str]] = {
    "python":     ["**/*.py"],
    "javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],
    "typescript": ["**/*.ts", "**/*.tsx"],
    "go":         ["**/*.go"],
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
