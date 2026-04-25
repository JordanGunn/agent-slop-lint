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
    # Step 1: File discovery
    find_result = find_kernel(
        root=root,
        globs=globs,
        excludes=excludes,
        hidden=hidden,
        no_ignore=no_ignore,
    )

    file_paths = [root / e.path for e in find_result.entries if e.type == "file"]
    errors: list[str] = list(find_result.errors)

    if not file_paths:
        return DepsResult(
            target=target,
            files=[],
            cycles=[],
            files_searched=find_result.total_found,
            errors=errors,
        )

    # Step 2: Build stem → path map for module resolution
    stem_to_path: dict[str, str] = {}
    for fp in file_paths:
        stem = fp.stem
        if stem not in stem_to_path:
            stem_to_path[stem] = str(fp)

    # Step 3: Extract import edges per file
    edges_by_file, extract_errors = _extract_all_imports(file_paths, language)
    all_edges = [e for edges in edges_by_file.values() for e in edges]
    errors.extend(extract_errors)

    # Step 4: Resolve modules to files and build adjacency
    # efferent_resolved: source_file -> set of resolved target abs_paths
    efferent_resolved: dict[str, set[str]] = {str(fp): set() for fp in file_paths}
    # imports_raw: source_file -> list of raw module strings
    imports_raw: dict[str, list[str]] = {str(fp): [] for fp in file_paths}

    for edge in all_edges:
        imports_raw[edge.source].append(edge.module)
        resolved = _resolve_module(edge.module, stem_to_path)
        if resolved and resolved != edge.source:
            efferent_resolved[edge.source].add(resolved)

    # Step 5: Build afferent map (reverse: who imports this file)
    afferent_map: dict[str, set[str]] = {str(fp): set() for fp in file_paths}
    for src, targets in efferent_resolved.items():
        for tgt in targets:
            if tgt in afferent_map:
                afferent_map[tgt].add(src)

    # Step 6: Detect cycles via DFS
    cycles = _detect_cycles(efferent_resolved)

    # Step 7: Build FileDeps list
    file_deps_list: list[FileDeps] = []

    target_abs: str | None = None
    if target:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = (root / target).resolve()
        target_abs = str(target_path)

    for fp in file_paths:
        fp_str = str(fp)

        # Target mode: only include the target file
        if target_abs is not None and fp_str != target_abs:
            continue

        # Deduplicate imports
        seen_modules: set[str] = set()
        unique_imports: list[str] = []
        for m in imports_raw[fp_str]:
            if m not in seen_modules:
                seen_modules.add(m)
                unique_imports.append(m)

        lang = _detect_file_language(fp)
        afferent_list = sorted(afferent_map[fp_str])
        ce = len(efferent_resolved[fp_str])
        ca = len(afferent_list)
        instability = ce / (ca + ce) if (ca + ce) > 0 else None

        file_deps_list.append(FileDeps(
            file=fp_str,
            language=lang,
            imports=unique_imports,
            imported_by=afferent_list,
            efferent=ce,
            afferent=ca,
            instability=instability,
        ))

    # Step 8: Sort by afferent descending
    file_deps_list.sort(key=lambda fd: fd.afferent, reverse=True)

    # Step 9: Apply max_results cap
    truncated = False
    if max_results is not None and len(file_deps_list) > max_results:
        file_deps_list = file_deps_list[:max_results]
        truncated = True

    # Filter cycles based on mode
    if target_abs is not None:
        # Include cycles that contain the target
        filtered_cycles = [c for c in cycles if target_abs in c]
    else:
        filtered_cycles = cycles

    return DepsResult(
        target=target,
        files=file_deps_list,
        cycles=filtered_cycles,
        files_searched=find_result.total_found,
        errors=errors,
        truncated=truncated,
    )


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
                        module=cap.text.strip('"\''),
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
        if stripped == "import (" or stripped.startswith("import ("):
            in_import_block = True
            continue
        if in_import_block:
            if stripped == ")":
                in_import_block = False
                continue
            m = pattern.search(stripped)
            if m:
                edges.append(ImportEdge(
                    source=str(fp),
                    module=m.group(1),
                    kind="go_import",
                    line=line_no,
                ))
        elif stripped.startswith("import "):
            m = pattern.search(stripped)
            if m:
                edges.append(ImportEdge(
                    source=str(fp),
                    module=m.group(1),
                    kind="go_import",
                    line=line_no,
                ))

    return edges


def _resolve_module(
    module: str,
    stem_to_path: dict[str, str],
) -> str | None:
    """Resolve a module string to an abs path in the scanned set.

    Best-effort: takes the last component of the module path and matches
    against file stems. Returns None if no match found.
    """
    # Take last component (e.g. "pkg.util.find" → "find", "./utils/helper" → "helper")
    last = module.replace("\\", "/").rstrip("/")
    last = last.split("/")[-1].split(".")[-1]

    # Strip leading dots (relative imports)
    last = last.lstrip(".")

    if not last:
        return None

    return stem_to_path.get(last)


def _detect_cycles(efferent: dict[str, set[str]]) -> list[list[str]]:
    """Detect cycles in the dependency graph using DFS.

    Returns list of cycles, each cycle as a list of abs paths.
    Only returns unique cycles (deduped by sorted tuple).
    """
    visited: set[str] = set()
    in_stack: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []
    seen_cycles: set[tuple[str, ...]] = set()

    def dfs(node: str) -> None:
        visited.add(node)
        in_stack.add(node)
        stack.append(node)

        for neighbor in efferent.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in in_stack:
                # Found a cycle — extract it
                cycle_start = stack.index(neighbor)
                cycle = stack[cycle_start:]
                key = tuple(sorted(cycle))
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    cycles.append(cycle[:])

        stack.pop()
        in_stack.discard(node)

    for node in efferent:
        if node not in visited:
            dfs(node)

    return cycles


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
    }
    return ext_map.get(ext)


