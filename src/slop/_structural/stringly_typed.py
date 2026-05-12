"""Stringly-typed parameter detection kernel.

A *stringly-typed* parameter is a function parameter annotated ``str``
(or left untyped) whose name is a domain-concept sentinel — words like
``status``, ``mode``, ``kind``, ``level``, ``format``, ``role``, ``action``.
These parameters almost always represent a finite set of string constants
that should instead be modelled as a ``Literal[...]`` union or an ``Enum``.

Detection strategy (two-pass)
------------------------------
1. **AST pass**: find Python function parameters that
   - are annotated ``str`` (or ``Optional[str]`` / ``str | None``), and
   - have a name that matches the sentinel word-list.
2. **Call-site pass**: use ripgrep to find call sites for each flagged
   function and collect the distinct string literals passed in the sentinel
   position. Functions where the call-site cardinality ≤ ``max_cardinality``
   (default 8) are reported — a small cardinality suggests an enum is
   appropriate.

When no call sites can be found (e.g. private API, or rg unavailable) the
function is still reported as advisory (severity = "warning").

Supported language: Python (full two-pass).
Other languages: AST-only pass (no call-site grep).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._ast.treesitter import detect_language, load_language
from slop._fs.find import find_kernel
from slop._text.grep import grep_kernel

# ---------------------------------------------------------------------------
# Sentinel names (lower-cased; matched as whole words or with suffixes _)
# ---------------------------------------------------------------------------

_SENTINEL_NAMES: frozenset[str] = frozenset({
    "status", "mode", "kind", "level", "format",
    "role", "action", "category", "severity", "phase",
    "stage", "style", "direction", "state", "type",
    "method", "strategy", "algorithm", "protocol",
    "encoding", "codec", "backend", "driver", "engine",
})

# Strip trailing _ (PEP 8 convention for shadowing builtins like type_)
_STRIP_TRAILING = re.compile(r'_+$')

# Type annotation text patterns that indicate a str annotation
_STR_ANNOTATION_RE = re.compile(
    r'\bstr\b'
)

_LANG_GLOBS: dict[str, list[str]] = {
    "python": ["**/*.py"],
    "c":      ["**/*.c", "**/*.h"],
    "cpp":    ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],
    "ruby":   ["**/*.rb"],
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StringlyEntry:
    """One function parameter identified as stringly-typed."""

    file: str
    function_name: str
    param_name: str
    param_line: int       # 1-based start of function
    annotated: bool       # True if parameter has str annotation; False if inferred
    call_site_literals: list[str] = field(default_factory=list)
    call_site_count: int = 0  # distinct literal values found at call sites


@dataclass
class StringlyResult:
    """Aggregated result from stringly_typed_kernel."""

    entries: list[StringlyEntry] = field(default_factory=list)
    functions_analyzed: int = 0
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def stringly_typed_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_cardinality: int = 8,
    require_str_annotation: bool = True,
) -> StringlyResult:
    """Detect functions with stringly-typed parameters.

    Args:
        root:                   Search root.
        languages:              Restrict to these languages.
        globs:                  Include glob patterns.
        excludes:               Exclude patterns.
        hidden:                 Search hidden files.
        no_ignore:              Ignore .gitignore rules.
        max_cardinality:        Report only when call-site literal cardinality
                                is ≤ this value (default: 8).
        require_str_annotation: When True, only report parameters with an
                                explicit ``str`` annotation. When False, also
                                report untyped sentinel-named parameters.
    """
    active_langs = (
        {l.lower() for l in languages} & set(_LANG_GLOBS)
        if languages else set(_LANG_GLOBS)
    )
    find_globs = list(globs) if globs else [
        g for l in sorted(active_langs) for g in _LANG_GLOBS.get(l, [])
    ]
    find_result = find_kernel(root=root, globs=find_globs, excludes=excludes,
                              hidden=hidden, no_ignore=no_ignore)
    files = [root / e.path for e in find_result.entries if e.type == "file"]

    entries: list[StringlyEntry] = []
    errors: list[str] = []
    total_functions = 0

    for fp in files:
        lang = detect_language(fp)
        if lang not in active_langs:
            continue
        if lang == "python":
            _scan_python_file(
                fp, root, entries, errors, require_str_annotation
            )
            total_functions += _count_python_functions(fp)
        elif lang == "c":
            total_functions += _scan_c_file(fp, root, entries, errors)
        elif lang == "cpp":
            total_functions += _scan_cpp_file(fp, root, entries, errors)
        elif lang == "ruby":
            total_functions += _scan_ruby_file(fp, root, entries, errors)

    # Pass 2: call-site literal collection via ripgrep
    _enrich_with_call_sites(entries, root, excludes or [], max_cardinality)

    entries.sort(key=lambda e: e.call_site_count)
    return StringlyResult(
        entries=entries,
        functions_analyzed=total_functions,
        files_searched=len(files),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Python AST pass
# ---------------------------------------------------------------------------


def _scan_python_file(
    fp: Path,
    root: Path,
    out: list[StringlyEntry],
    errors: list[str],
    require_str_annotation: bool,
) -> None:
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
        _walk_python_functions(tree.root_node, content, rel, out, require_str_annotation)
    except Exception as exc:
        errors.append(f"{fp}: {exc}")


def _walk_python_functions(
    root_node: object,
    content: bytes,
    rel: str,
    out: list[StringlyEntry],
    require_str_annotation: bool,
) -> None:
    fn_types = frozenset({"function_definition", "async_function_definition"})
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type in fn_types:  # type: ignore[attr-defined]
            _process_python_function(node, content, rel, out, require_str_annotation)
        stack.extend(node.children)  # type: ignore[attr-defined]


def _process_python_function(
    fn_node: object,
    content: bytes,
    rel: str,
    out: list[StringlyEntry],
    require_str_annotation: bool,
) -> None:
    name_node = fn_node.child_by_field_name("name")  # type: ignore[attr-defined]
    fn_name = (
        content[name_node.start_byte:name_node.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
        if name_node else "<anonymous>"
    )
    fn_line = fn_node.start_point[0] + 1  # type: ignore[attr-defined]

    params_node = fn_node.child_by_field_name("parameters")  # type: ignore[attr-defined]
    if params_node is None:
        return

    for child in params_node.children:  # type: ignore[attr-defined]
        ptype = child.type  # type: ignore[attr-defined]
        param_name = None
        has_str_annotation = False

        if ptype == "identifier":
            raw = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            param_name = raw
            has_str_annotation = False  # untyped

        elif ptype in ("typed_parameter", "typed_default_parameter"):
            name_n = child.child_by_field_name("name") or next(  # type: ignore[attr-defined]
                (c for c in child.children if c.type == "identifier"), None  # type: ignore[attr-defined]
            )
            type_n = child.child_by_field_name("type")  # type: ignore[attr-defined]
            if name_n is None:
                continue
            param_name = content[name_n.start_byte:name_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
            if type_n is not None:
                type_text = content[type_n.start_byte:type_n.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                has_str_annotation = bool(_STR_ANNOTATION_RE.search(type_text))

        if param_name is None:
            continue
        if require_str_annotation and not has_str_annotation:
            continue

        # Check sentinel names
        clean_name = _STRIP_TRAILING.sub("", param_name).lower()
        if clean_name in _SENTINEL_NAMES:
            out.append(StringlyEntry(
                file=rel,
                function_name=fn_name,
                param_name=param_name,
                param_line=fn_line,
                annotated=has_str_annotation,
            ))


def _count_python_functions(fp: Path) -> int:
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
# Call-site enrichment via ripgrep
# ---------------------------------------------------------------------------


def _enrich_with_call_sites(
    entries: list[StringlyEntry],
    root: Path,
    excludes: list[str],
    max_cardinality: int,
) -> None:
    """For each entry, search for call-site string literals (best-effort)."""
    if not entries:
        return

    # Build a dict from function name → list of entries
    by_fn: dict[str, list[StringlyEntry]] = {}
    for e in entries:
        by_fn.setdefault(e.function_name, []).append(e)

    # One rg search per unique function name
    for fn_name, fn_entries in by_fn.items():
        # Pattern: fn_name(... "literal" ...) — approximate
        pattern = rf'\b{re.escape(fn_name)}\s*\([^)]*["\']([^"\']+)["\']'
        try:
            result = grep_kernel(
                patterns=[{"kind": "regex", "value": pattern}],
                root=root,
                excludes=excludes,
            )
            # Extract string literal captures from match content
            literals: set[str] = set()
            lit_re = re.compile(r'["\']([^"\']{1,50})["\']')
            for m in result.matches:
                for lit_m in lit_re.finditer(m.content):
                    literals.add(lit_m.group(1))
            for e in fn_entries:
                e.call_site_literals = sorted(literals)
                e.call_site_count = len(literals)
        except Exception:
            pass  # Best-effort; leave call_site_count=0


# ---------------------------------------------------------------------------
# C AST pass
# ---------------------------------------------------------------------------


def _scan_c_file(
    fp: Path,
    root: Path,
    out: list[StringlyEntry],
    errors: list[str],
) -> int:
    """Scan one C file for ``char *`` parameters with sentinel-shaped names.

    Walks every ``function_definition`` and inspects its ``parameter_list``.
    A parameter is flagged when:

    - Its declarator chain ends in a ``pointer_declarator`` whose innermost
      identifier is the parameter name.
    - The parameter type is ``char`` (with optional ``const`` qualifier;
      ``const char *`` is the canonical C "string parameter" shape).
    - The parameter name (lowercased, stripped of trailing ``_``) is in
      ``_SENTINEL_NAMES``.

    Returns the count of functions analysed.
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
        else:
            stack.extend(node.children)  # type: ignore[attr-defined]
    return fn_count


def _process_c_function(
    fn_node: object,
    content: bytes,
    rel: str,
    out: list[StringlyEntry],
) -> None:
    """Extract sentinel-shaped ``char *`` parameters from one C function."""
    fn_name = _c_fn_name(fn_node, content)
    fn_line = fn_node.start_point[0] + 1  # type: ignore[attr-defined]

    declarator = fn_node.child_by_field_name("declarator")  # type: ignore[attr-defined]
    while declarator is not None and declarator.type == "pointer_declarator":  # type: ignore[attr-defined]
        declarator = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
    if declarator is None or declarator.type != "function_declarator":  # type: ignore[attr-defined]
        return

    plist = declarator.child_by_field_name("parameters")  # type: ignore[attr-defined]
    if plist is None:
        return

    for param in plist.children:  # type: ignore[attr-defined]
        if param.type != "parameter_declaration":  # type: ignore[attr-defined]
            continue

        is_char_ptr = False
        ptr_decl = None
        for child in param.children:  # type: ignore[attr-defined]
            ctype = child.type  # type: ignore[attr-defined]
            if ctype == "primitive_type":
                ptext = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if ptext.strip() == "char":
                    is_char_ptr = True
            elif ctype == "pointer_declarator":
                ptr_decl = child

        if not is_char_ptr or ptr_decl is None:
            continue

        # Find the parameter identifier inside the (possibly nested)
        # pointer_declarator chain.
        cur = ptr_decl
        param_name: str | None = None
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

        sentinel_key = _STRIP_TRAILING.sub("", param_name).lower()
        if sentinel_key not in _SENTINEL_NAMES:
            continue

        out.append(StringlyEntry(
            file=rel,
            function_name=fn_name,
            param_name=param_name,
            param_line=fn_line,
            annotated=True,    # ``char *`` is the explicit annotation
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


# ---------------------------------------------------------------------------
# C++ AST pass
# ---------------------------------------------------------------------------


def _scan_cpp_file(
    fp: Path,
    root: Path,
    out: list[StringlyEntry],
    errors: list[str],
) -> int:
    """Scan one C++ file for sentinel-shaped string parameters.

    Flags ``char *``, ``const char *``, ``std::string``, and
    ``std::string_view`` parameters whose name (lowercased, stripped of
    trailing ``_``) is in ``_SENTINEL_NAMES``. Returns function count.
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
        else:
            stack.extend(node.children)  # type: ignore[attr-defined]
    return fn_count


def _process_cpp_function(
    fn_node: object,
    content: bytes,
    rel: str,
    out: list[StringlyEntry],
) -> None:
    """Extract sentinel-shaped string-typed parameters from a C++ function."""
    fn_name = _cpp_fn_name_local(fn_node, content)
    fn_line = fn_node.start_point[0] + 1  # type: ignore[attr-defined]

    declarator = fn_node.child_by_field_name("declarator")  # type: ignore[attr-defined]
    while declarator is not None and declarator.type in (  # type: ignore[attr-defined]
        "pointer_declarator", "reference_declarator", "parenthesized_declarator",
    ):
        declarator = declarator.child_by_field_name("declarator")  # type: ignore[attr-defined]
    if declarator is None or declarator.type != "function_declarator":  # type: ignore[attr-defined]
        return

    plist = declarator.child_by_field_name("parameters")  # type: ignore[attr-defined]
    if plist is None:
        return

    for param in plist.children:  # type: ignore[attr-defined]
        if param.type != "parameter_declaration":  # type: ignore[attr-defined]
            continue

        is_string = False
        # ``char`` primitive_type with a pointer_declarator or
        # reference_declarator child → ``char*`` / ``char&`` parameter.
        # ``std::string`` / ``std::string_view`` appear as
        # qualified_identifier children with leaf "string"/"string_view".
        ptr_or_ref = None
        for child in param.children:  # type: ignore[attr-defined]
            ctype = child.type  # type: ignore[attr-defined]
            if ctype == "primitive_type":
                ptext = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if ptext.strip() == "char":
                    is_string = True
            elif ctype in ("pointer_declarator", "reference_declarator"):
                ptr_or_ref = child
            elif ctype == "qualified_identifier":
                qtext = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if qtext.strip() in (
                    "std::string", "std::string_view",
                    "std::wstring", "std::wstring_view",
                ):
                    is_string = True
            elif ctype == "type_identifier":
                ttext = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                if ttext.strip() in ("string", "string_view", "wstring", "wstring_view"):
                    is_string = True

        if not is_string:
            continue

        # Find the parameter identifier. For pointer/reference, it's
        # inside the declarator chain. For value-passed std::string, it's
        # a direct identifier child of parameter_declaration.
        param_name: str | None = None
        if ptr_or_ref is not None:
            cur = ptr_or_ref
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
        else:
            for child in param.children:  # type: ignore[attr-defined]
                if child.type == "identifier":  # type: ignore[attr-defined]
                    param_name = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    break

        if param_name is None:
            continue

        sentinel_key = _STRIP_TRAILING.sub("", param_name).lower()
        if sentinel_key not in _SENTINEL_NAMES:
            continue

        out.append(StringlyEntry(
            file=rel,
            function_name=fn_name,
            param_name=param_name,
            param_line=fn_line,
            annotated=True,
        ))


def _cpp_fn_name_local(fn_node: object, content: bytes) -> str:
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


# ---------------------------------------------------------------------------
# Ruby AST pass
# ---------------------------------------------------------------------------


def _scan_ruby_file(
    fp: Path,
    root: Path,
    out: list[StringlyEntry],
    errors: list[str],
) -> int:
    """Scan one Ruby file for sentinel-shaped parameters.

    Ruby methods don't carry type annotations, but the convention of
    string / symbol "kind" / "mode" / "level" parameters is common.
    Flags any ``method`` or ``singleton_method`` parameter whose name
    (lowercased, trailing ``_`` stripped) is in ``_SENTINEL_NAMES``.
    """
    tree_lang = load_language("ruby")
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
        if node.type in ("method", "singleton_method"):  # type: ignore[attr-defined]
            fn_count += 1
            _process_ruby_method(node, content, rel, out)
        # Continue walking — Ruby allows methods nested inside class /
        # module bodies.
        stack.extend(node.children)  # type: ignore[attr-defined]
    return fn_count


def _process_ruby_method(
    node: object,
    content: bytes,
    rel: str,
    out: list[StringlyEntry],
) -> None:
    """Extract sentinel-shaped parameters from a Ruby method."""
    fn_name = _ruby_fn_name_local(node, content)
    fn_line = node.start_point[0] + 1  # type: ignore[attr-defined]

    # Find method_parameters child
    params_node = None
    for child in node.children:  # type: ignore[attr-defined]
        if child.type == "method_parameters":  # type: ignore[attr-defined]
            params_node = child
            break
    if params_node is None:
        return

    # Walk parameter children for identifiers (and for default-valued
    # parameters, optional_parameter and keyword_parameter shapes).
    for child in params_node.children:  # type: ignore[attr-defined]
        ctype = child.type  # type: ignore[attr-defined]
        param_name: str | None = None
        if ctype == "identifier":
            param_name = content[child.start_byte:child.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
        elif ctype in ("optional_parameter", "keyword_parameter"):
            # First identifier child is the parameter name.
            for sub in child.children:  # type: ignore[attr-defined]
                if sub.type == "identifier":  # type: ignore[attr-defined]
                    param_name = content[sub.start_byte:sub.end_byte].decode(errors="replace")  # type: ignore[attr-defined]
                    break

        if param_name is None:
            continue

        sentinel_key = _STRIP_TRAILING.sub("", param_name).lower()
        if sentinel_key not in _SENTINEL_NAMES:
            continue

        out.append(StringlyEntry(
            file=rel,
            function_name=fn_name,
            param_name=param_name,
            param_line=fn_line,
            # Ruby has no static type annotations, so ``annotated``
            # reflects "the parameter is named for a sentinel" rather
            # than "the parameter is annotated str".
            annotated=False,
        ))


def _ruby_fn_name_local(node: object, content: bytes) -> str:
    """Walk Ruby method children for the name node."""
    saw_def = False
    saw_self = False
    saw_dot = False
    for child in node.children:  # type: ignore[attr-defined]
        ctype = child.type  # type: ignore[attr-defined]
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
            return content[child.start_byte:child.end_byte].decode(errors="replace").strip()  # type: ignore[attr-defined]
    return "<anonymous>"
