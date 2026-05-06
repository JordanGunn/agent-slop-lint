"""Deps kernel - module dependency graph analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._fs.find import find_kernel

# Tree-sitter import queries per language: list of (query_string, kind_label)
IMPORT_QUERIES: dict[str, list[tuple[str, str]]] = {
    "python": [
        ("(import_statement name: (dotted_name) @module)", "import"),
        ("(import_from_statement module_name: (dotted_name) @module)", "from_import"),
    ],
    "javascript": [
        ("(import_statement source: (string (string_fragment) @module))", "esm"),
    ],
    "typescript": [
        ("(import_statement source: (string (string_fragment) @module))", "esm"),
    ],
    "go": [
        ("(import_spec path: (interpreted_string_literal) @module)", "go_import"),
    ],
    "java": [
        ("(import_declaration (scoped_identifier) @module)", "java_import"),
    ],
    "c_sharp": [
        ("(using_directive (identifier) @module)", "csharp_using"),
        ("(using_directive (qualified_name) @module)", "csharp_using"),
    ],
    "julia": [
        # `using Foo` / `using Foo, Bar`
        ("(using_statement (identifier) @module)", "julia_using"),
        # `using Foo.Bar`
        ("(using_statement (scoped_identifier) @module)", "julia_using"),
        # `using Foo: a, b` — only the leading identifier is the module
        ("(using_statement (selected_import . (identifier) @module))", "julia_using"),
        # `import Foo` / `import Foo, Bar`
        ("(import_statement (identifier) @module)", "julia_import"),
        # `import Foo.Bar`
        ("(import_statement (scoped_identifier) @module)", "julia_import"),
        # `import Base: show` — only the leading identifier is the module
        ("(import_statement (selected_import . (identifier) @module))", "julia_import"),
    ],
    "c": [
        # `#include "foo.h"` — capture the inner content (already unquoted)
        ('(preproc_include path: (string_literal (string_content) @module))',
         "include_local"),
        # `#include <stdio.h>` — system_lib_string includes angle brackets;
        # they're stripped in the capture loop alongside quote chars.
        ('(preproc_include path: (system_lib_string) @module)',
         "include_system"),
    ],
    "cpp": [
        # Same shape as C — tree-sitter-cpp inherits the C preprocessor
        # node types.
        ('(preproc_include path: (string_literal (string_content) @module))',
         "include_local"),
        ('(preproc_include path: (system_lib_string) @module)',
         "include_system"),
    ],
}

# Text-tier per-language regex fallback (applied to raw file content)
TEXT_IMPORT_REGEXES: dict[str, list[tuple[str, str]]] = {
    "python": [
        (r"^import\s+([\w.]+)", "import"),
        (r"^from\s+([\w.]+)\s+import", "from_import"),
    ],
    "javascript": [
        (r"""import\s+.*from\s+['"]([^'"]+)['"]""", "esm"),
        (r"""require\(['"]([^'"]+)['"]\)""", "require"),
    ],
    "typescript": [
        (r"""import\s+.*from\s+['"]([^'"]+)['"]""", "esm"),
    ],
    "go": [
        (r'"([^"]+)"', "go_import"),  # applied only inside import blocks
    ],
    "rust": [
        (r"^use\s+([\w:]+)", "use"),
    ],
    "java": [
        (r"^import\s+([\w.]+);", "java_import"),
    ],
    "c_sharp": [
        (r"^using\s+([\w.]+)\s*;", "csharp_using"),
    ],
    "julia": [
        # `using Mod`, `using Mod1, Mod2`, `using Foo.Bar`
        (r"^\s*using\s+([\w.]+)", "julia_using"),
        # `using Foo: a, b` — captures Foo
        (r"^\s*using\s+([\w.]+)\s*:", "julia_using"),
        # `import Foo`, `import Foo.Bar`
        (r"^\s*import\s+([\w.]+)", "julia_import"),
        # `import Foo: a, b` — captures Foo
        (r"^\s*import\s+([\w.]+)\s*:", "julia_import"),
    ],
    "c": [
        # `#include "foo.h"` — captures `foo.h`
        (r'^\s*#\s*include\s+"([^"]+)"', "include_local"),
        # `#include <stdio.h>` — captures `stdio.h`
        (r"^\s*#\s*include\s+<([^>]+)>", "include_system"),
    ],
    "cpp": [
        (r'^\s*#\s*include\s+"([^"]+)"', "include_local"),
        (r"^\s*#\s*include\s+<([^>]+)>", "include_system"),
    ],
}


@dataclass
class ImportEdge:
    """A single import statement extracted from a file."""

    source: str    # abs path of importing file
    module: str    # raw module string from import statement
    kind: str      # "import" | "from_import" | "esm" | "require" | etc.
    line: int      # 1-based line number


@dataclass
class FileDeps:
    """Dependency info for a single file."""

    file: str                    # abs path
    language: str | None
    imports: list[str]           # module names this file imports (efferent)
    imported_by: list[str]       # abs paths of files that import this one (afferent)
    efferent: int                # Ce = len(unique external modules)
    afferent: int                # Ca = len(imported_by)
    instability: float | None    # Ce / (Ca + Ce); None if Ca + Ce == 0


@dataclass
class DepsResult:
    """Aggregated dependency graph result."""

    target: str | None           # None = full graph mode
    files: list[FileDeps]        # per-file info (sorted by afferent desc)
    cycles: list[list[str]]      # each inner list = one cycle (abs paths)
    files_searched: int
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


@dataclass
class _DiscoveredFiles:
    """File discovery output used by the dependency pipeline."""

    paths: list[Path]
    total_found: int
    errors: list[str]


@dataclass
class _DependencyGraph:
    """Resolved dependency graph plus raw imports for result rendering."""

    imports_raw: dict[str, list[str]]
    efferent: dict[str, set[str]]
    afferent: dict[str, set[str]]
    cycles: list[list[str]]
    errors: list[str]


@dataclass
class _ModuleIndex:
    """Best-effort local import resolver indexes."""

    exact: dict[str, str]
    stem: dict[str, str]


def deps_kernel(
    root: Path,
    *,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    target: str | None = None,
    language: str | None = None,
    max_depth: int | None = None,  # noqa: ARG001 — reserved: transitive depth limit
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
) -> DepsResult:
    """Compute module dependency graph for a codebase.

    Args:
        root: Search root directory
        globs: Include glob patterns
        excludes: Exclude glob patterns
        target: Focus on one file (rel or abs path); None = full graph mode
        language: Tree-sitter language override
        max_depth: Transitive depth limit (None = unlimited)
        hidden: Search hidden files
        no_ignore: Don't respect gitignore
        max_results: Cap on files in output

    Returns:
        DepsResult with per-file dependency info and cycles
    """
    discovered = _discover_dependency_files(
        root=root, globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore,
    )

    if not discovered.paths:
        return _empty_result(
            target=target,
            files_searched=discovered.total_found,
            errors=discovered.errors,
        )

    graph = _build_dependency_graph(root, discovered.paths, language)
    errors = [*discovered.errors, *graph.errors]
    target_abs = _resolve_target(root, target)
    file_deps_list = _build_file_deps(
        file_paths=discovered.paths,
        imports_raw=graph.imports_raw,
        efferent=graph.efferent,
        afferent=graph.afferent,
        target_abs=target_abs,
    )
    file_deps_list, truncated = _sort_and_cap_file_deps(file_deps_list, max_results)

    return DepsResult(
        target=target,
        files=file_deps_list,
        cycles=_filter_cycles(graph.cycles, target_abs),
        files_searched=discovered.total_found,
        errors=errors,
        truncated=truncated,
    )


def _empty_result(
    *,
    target: str | None,
    files_searched: int,
    errors: list[str],
) -> DepsResult:
    """Build an empty dependency result."""
    return DepsResult(
        target=target,
        files=[],
        cycles=[],
        files_searched=files_searched,
        errors=errors,
    )


def _discover_dependency_files(
    *,
    root: Path,
    globs: list[str] | None,
    excludes: list[str] | None,
    hidden: bool,
    no_ignore: bool,
) -> _DiscoveredFiles:
    """Find candidate source files for dependency analysis."""
    find_result = find_kernel(
        root=root,
        globs=globs,
        excludes=excludes,
        hidden=hidden,
        no_ignore=no_ignore,
    )
    return _DiscoveredFiles(
        paths=[root / e.path for e in find_result.entries if e.type == "file"],
        total_found=find_result.total_found,
        errors=list(find_result.errors),
    )


def _build_dependency_graph(
    root: Path,
    file_paths: list[Path],
    language_override: str | None,
) -> _DependencyGraph:
    """Extract imports and build local dependency graph structures."""
    module_index = _build_module_index(root, file_paths)
    edges_by_file, extract_errors = _extract_all_imports(file_paths, language_override)
    all_edges = [edge for edges in edges_by_file.values() for edge in edges]
    imports_raw, efferent = _resolve_edges(file_paths, all_edges, module_index)
    afferent = _reverse_adjacency(file_paths, efferent)
    return _DependencyGraph(
        imports_raw=imports_raw,
        efferent=efferent,
        afferent=afferent,
        cycles=_detect_cycles(efferent),
        errors=extract_errors,
    )


def _build_module_index(root: Path, file_paths: list[Path]) -> _ModuleIndex:
    """Build exact module-path and fallback stem indexes."""
    exact: dict[str, str] = {}
    stem: dict[str, str] = {}
    for fp in file_paths:
        fp_str = str(fp)
        stem.setdefault(fp.stem, fp_str)
        # Also index by the full filename (with extension). This is
        # primarily for C/C++ ``#include "foo.h"`` resolution from a peer
        # file; languages whose import strings do not include the file
        # extension never query this key.
        stem.setdefault(fp.name, fp_str)
        for name in _module_names_for_path(root, fp):
            exact.setdefault(name, fp_str)
        # Index by extension-preserving relative path so
        # ``#include "subdir/foo.h"`` resolves exactly to subdir/foo.h.
        try:
            rel = fp.relative_to(root)
            rel_with_ext = "/".join(rel.parts)
            if rel_with_ext:
                exact.setdefault(rel_with_ext, fp_str)
        except ValueError:
            pass
    return _ModuleIndex(exact=exact, stem=stem)


def _module_names_for_path(root: Path, fp: Path) -> list[str]:
    """Return local module names represented by a source path."""
    try:
        rel = fp.relative_to(root)
    except ValueError:
        rel = fp

    without_suffix = rel.with_suffix("")
    dotted = ".".join(without_suffix.parts)
    slash = "/".join(without_suffix.parts)
    names = [dotted, slash]

    if fp.name == "__init__.py" and without_suffix.parent.parts:
        package_dotted = ".".join(without_suffix.parent.parts)
        package_slash = "/".join(without_suffix.parent.parts)
        names.extend([package_dotted, package_slash])

    return _unique_strings(name for name in names if name)


def _resolve_edges(
    file_paths: list[Path],
    edges: list[ImportEdge],
    module_index: _ModuleIndex,
) -> tuple[dict[str, list[str]], dict[str, set[str]]]:
    """Resolve import edges to raw imports and local efferent adjacency."""
    efferent: dict[str, set[str]] = {str(fp): set() for fp in file_paths}
    imports_raw: dict[str, list[str]] = {str(fp): [] for fp in file_paths}

    for edge in edges:
        imports_raw[edge.source].append(edge.module)
        resolved = _resolve_module(edge.module, module_index)
        if resolved and resolved != edge.source:
            efferent[edge.source].add(resolved)

    return imports_raw, efferent


def _reverse_adjacency(
    file_paths: list[Path],
    efferent: dict[str, set[str]],
) -> dict[str, set[str]]:
    """Build reverse dependency adjacency."""
    afferent: dict[str, set[str]] = {str(fp): set() for fp in file_paths}
    for src, targets in efferent.items():
        for tgt in targets:
            if tgt in afferent:
                afferent[tgt].add(src)
    return afferent


def _resolve_target(root: Path, target: str | None) -> str | None:
    """Resolve optional target path using the historical kernel semantics."""
    if target is None:
        return None
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = (root / target).resolve()
    return str(target_path)


def _build_file_deps(
    *,
    file_paths: list[Path],
    imports_raw: dict[str, list[str]],
    efferent: dict[str, set[str]],
    afferent: dict[str, set[str]],
    target_abs: str | None,
) -> list[FileDeps]:
    """Build per-file dependency records from graph structures."""
    file_deps: list[FileDeps] = []
    for fp in file_paths:
        fp_str = str(fp)
        if target_abs is not None and fp_str != target_abs:
            continue
        afferent_list = sorted(afferent[fp_str])
        ce = len(efferent[fp_str])
        ca = len(afferent_list)
        file_deps.append(FileDeps(
            file=fp_str,
            language=_detect_file_language(fp),
            imports=_unique_imports(imports_raw[fp_str]),
            imported_by=afferent_list,
            efferent=ce,
            afferent=ca,
            instability=ce / (ca + ce) if (ca + ce) > 0 else None,
        ))
    return file_deps


def _unique_imports(imports: list[str]) -> list[str]:
    """Deduplicate imports while preserving first-seen order."""
    return _unique_strings(imports)


def _unique_strings(values) -> list[str]:
    """Deduplicate strings while preserving first-seen order."""
    seen_modules: set[str] = set()
    unique_imports: list[str] = []
    for module in values:
        if module not in seen_modules:
            seen_modules.add(module)
            unique_imports.append(module)
    return unique_imports


def _sort_and_cap_file_deps(
    file_deps: list[FileDeps],
    max_results: int | None,
) -> tuple[list[FileDeps], bool]:
    """Sort dependency records and apply the optional result cap."""
    file_deps.sort(key=lambda fd: fd.afferent, reverse=True)
    if max_results is not None and len(file_deps) > max_results:
        return file_deps[:max_results], True
    return file_deps, False


def _filter_cycles(cycles: list[list[str]], target_abs: str | None) -> list[list[str]]:
    """Apply target-mode cycle filtering."""
    if target_abs is None:
        return cycles
    return [cycle for cycle in cycles if target_abs in cycle]


def _extract_all_imports(
    file_paths: list[Path],
    language_override: str | None,
) -> tuple[dict[str, list[ImportEdge]], list[str]]:
    """Extract import edges from all files.

    Tries tree-sitter first; falls back to text-tier regex per file.
    Returns (edges_by_file, errors).
    """
    edges_by_file: dict[str, list[ImportEdge]] = {str(fp): [] for fp in file_paths}
    errors: list[str] = []

    for fp in file_paths:
        fp_str = str(fp)
        lang = language_override or _detect_file_language(fp)
        if lang is None:
            continue

        extracted = False
        if lang in IMPORT_QUERIES:
            try:
                edges = _extract_imports_ast(fp, lang)
                edges_by_file[fp_str] = edges
                extracted = True
            except Exception as e:
                errors.append(f"{fp}: AST import extraction failed: {e}")

        if not extracted and lang in TEXT_IMPORT_REGEXES:
            try:
                edges = _extract_imports_text(fp, lang)
                edges_by_file[fp_str] = edges
            except Exception as e:
                errors.append(f"{fp}: text import extraction failed: {e}")

    return edges_by_file, errors


def _extract_imports_ast(fp: Path, language: str) -> list[ImportEdge]:
    """Extract import edges using tree-sitter AST."""
    from slop._ast.query import query_kernel

    queries = IMPORT_QUERIES.get(language, [])
    edges: list[ImportEdge] = []

    for query_str, kind in queries:
        result = query_kernel(files=[fp], query_str=query_str, language=language)
        for match in result.matches:
            for cap in match.captures:
                if cap.name == "module":
                    edges.append(ImportEdge(
                        source=str(fp),
                        # Strip surrounding quotes (most langs) and angle
                        # brackets (C/C++ system includes: ``<stdio.h>``).
                        module=cap.text.strip('"\'<>'),
                        kind=kind,
                        line=cap.line,
                    ))
    return edges


def _extract_imports_text(fp: Path, language: str) -> list[ImportEdge]:
    """Extract import edges using regex on raw file content (text-tier fallback)."""
    regexes = TEXT_IMPORT_REGEXES.get(language, [])
    if not regexes:
        return []

    try:
        content = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    edges: list[ImportEdge] = []

    # Special handling for Go: only match inside import blocks
    if language == "go":
        return _extract_go_imports_text(fp, content)

    for line_no, line in enumerate(content.splitlines(), start=1):
        for pattern, kind in regexes:
            m = re.match(pattern, line)
            if m:
                module = m.group(1)
                edges.append(ImportEdge(
                    source=str(fp),
                    module=module,
                    kind=kind,
                    line=line_no,
                ))
                break  # Only first matching pattern per line

    return edges


def _extract_go_imports_text(fp: Path, content: str) -> list[ImportEdge]:
    """Extract Go imports from import blocks."""
    edges: list[ImportEdge] = []
    in_import_block = False
    pattern = re.compile(r'"([^"]+)"')

    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if _is_go_import_block_start(stripped):
            in_import_block = True
            continue

        if in_import_block:
            if _is_go_import_block_end(stripped):
                in_import_block = False
                continue
            _append_go_import_edge(edges, fp, line_no, stripped, pattern)
        elif stripped.startswith("import "):
            _append_go_import_edge(edges, fp, line_no, stripped, pattern)

    return edges


def _is_go_import_block_start(stripped: str) -> bool:
    """Return whether a Go line starts an import block."""
    return stripped == "import (" or stripped.startswith("import (")


def _is_go_import_block_end(stripped: str) -> bool:
    """Return whether a Go line ends an import block."""
    return stripped == ")"


def _append_go_import_edge(
    edges: list[ImportEdge],
    fp: Path,
    line_no: int,
    stripped: str,
    pattern: re.Pattern[str],
) -> None:
    """Append a Go import edge when the line contains an import path."""
    match = pattern.search(stripped)
    if match:
        edges.append(ImportEdge(
            source=str(fp),
            module=match.group(1),
            kind="go_import",
            line=line_no,
        ))


def _resolve_module(
    module: str,
    module_index: _ModuleIndex,
) -> str | None:
    """Resolve a module string to an abs path in the scanned set.

    Best-effort: prefer an exact local module path, then fall back to the
    historical last-component stem match. Returns None if no match is found.
    """
    normalized = _normalize_module_name(module)
    if not normalized:
        return None

    exact = module_index.exact.get(normalized) or module_index.exact.get(
        normalized.replace(".", "/")
    )
    if exact:
        return exact

    last = normalized.replace("\\", "/").rstrip("/")
    last = last.split("/")[-1]
    # Try the full last component first ("foo.h" — C/C++ include); fall
    # back to the suffix-stripped last component (Python dotted-name
    # convention, "foo.bar.baz" → "baz").
    return module_index.stem.get(last) or module_index.stem.get(
        last.split(".")[-1]
    )


def _normalize_module_name(module: str) -> str:
    """Normalize an import string for local best-effort matching."""
    normalized = module.strip().strip('"\'').replace("\\", "/").rstrip("/")
    normalized = normalized.lstrip(".")
    if normalized.startswith("/"):
        normalized = normalized.lstrip("/")
    return normalized


def _detect_cycles(efferent: dict[str, set[str]]) -> list[list[str]]:
    """Detect cycles in the dependency graph using Tarjan SCC.

    Returns list of cycles, each cycle as a list of abs paths.
    Each cycle is a strongly connected component with more than one node.
    """
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in sorted(efferent.get(node, set())):
            if neighbor not in indexes:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[neighbor])

        if lowlinks[node] == indexes[node]:
            component = _pop_scc(node, stack, on_stack)
            if len(component) > 1:
                cycles.append(component)

    for node in efferent:
        if node not in indexes:
            strongconnect(node)

    return cycles


def _pop_scc(node: str, stack: list[str], on_stack: set[str]) -> list[str]:
    """Pop one strongly connected component from Tarjan state."""
    component: list[str] = []
    while stack:
        current = stack.pop()
        on_stack.remove(current)
        component.append(current)
        if current == node:
            break
    return sorted(component)


def _detect_file_language(fp: Path) -> str | None:
    """Detect language from file extension."""
    ext = fp.suffix.lower()
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cs": "c_sharp",
        ".jl": "julia",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".hxx": "cpp",
    }
    return ext_map.get(ext)
