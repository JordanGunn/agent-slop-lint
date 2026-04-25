"""CK kernel — Chidamber & Kemerer class-level metrics.

Computes CBO (Coupling Between Object Classes), DIT (Depth of Inheritance
Tree), NOC (Number of Children), and WMC (Weighted Methods per Class) per
class/struct/interface across a codebase via tree-sitter AST traversal.

Cross-kernel composition:
    ``ck`` → ``ccx`` is allowed (for WMC). ``ccx`` → ``ck`` is forbidden
    (downward-only composition rule).

CBO resolution:
    Name-based, not type-based. The kernel builds a registry of all class
    names in the codebase, then scans each class body/impl/method bodies
    for identifiers matching a known class name (excluding self). The
    approximation is deterministic and catches the majority of real coupling.

Language model:
    Python, Java, TypeScript, JavaScript use body-based classes (methods are
    children of the class body). Go uses receiver-based methods (at module
    scope, matched by receiver type). Rust uses impl-block methods (inside
    impl items, matched by target type).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tree_sitter

from slop._structural.ccx import ccx_kernel
from slop._fs.find import find_kernel
from slop._ast.treesitter import detect_language, load_language

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ClassMetrics:
    """Per-class Chidamber & Kemerer metrics."""

    name: str
    file: str
    path: str
    line: int
    end_line: int
    language: str
    kind: str                     # "class"|"struct"|"interface"|"trait"|"enum"
    cbo: int
    dit: int
    noc: int
    wmc: int
    method_count: int
    superclasses: list[str]
    interpretation: str


@dataclass
class CkResult:
    """Aggregated CK metrics result."""

    classes: list[ClassMetrics]
    files_searched: int
    classes_analyzed: int
    languages: dict[str, int]
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


@dataclass
class _ClassInfo:
    """Intermediate class record collected during AST walk."""

    name: str
    file: str
    path: str
    line: int
    end_line: int
    language: str
    kind: str
    superclasses: list[str]
    scan_nodes: list[Any]         # AST nodes to scan for CBO references
    method_count: int = 0


# ---------------------------------------------------------------------------
# Per-language configuration
# ---------------------------------------------------------------------------

# Type for superclass extraction: (class_node, content) -> list[parent_names]
SuperclassExtractor = Callable[[Any, bytes], list[str]]


@dataclass(frozen=True)
class _CkLangConfig:
    """Per-language node-type strategy for class metrics."""

    class_nodes: frozenset[str]
    class_name_field: str
    body_field: str | None
    method_nodes: frozenset[str]
    ref_node_types: frozenset[str]
    extract_superclasses: SuperclassExtractor
    kind_label: str = "class"
    is_receiver_based: bool = False
    is_impl_based: bool = False


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


# ---------------------------------------------------------------------------
# Superclass extractors (per-language)
# ---------------------------------------------------------------------------


def _extract_python_superclasses(node, content: bytes) -> list[str]:
    sc_node = node.child_by_field_name("superclasses")
    if sc_node is None:
        return []
    result: list[str] = []
    for child in sc_node.children:
        if child.type == "identifier":
            result.append(_node_text(child, content))
        elif child.type == "attribute":
            parts = _node_text(child, content).split(".")
            result.append(parts[-1])
    return result


def _extract_csharp_superclasses(node, content: bytes) -> list[str]:
    """C#: base_list contains identifier children (classes + interfaces)."""
    result: list[str] = []
    for child in node.children:
        if child.type == "base_list":
            for gc in child.children:
                if gc.type == "identifier":
                    result.append(_node_text(gc, content))
    return result


def _extract_java_superclasses(node, content: bytes) -> list[str]:
    result: list[str] = []
    # extends (single superclass)
    sc = node.child_by_field_name("superclass")
    if sc is not None:
        for child in sc.children:
            if child.type == "type_identifier":
                result.append(_node_text(child, content))
    # implements (interfaces)
    ifaces = node.child_by_field_name("interfaces")
    if ifaces is not None:
        for child in ifaces.children:
            if child.type == "type_list":
                for tc in child.children:
                    if tc.type == "type_identifier":
                        result.append(_node_text(tc, content))
            elif child.type == "type_identifier":
                result.append(_node_text(child, content))
    return result


def _extract_ts_superclasses(node, content: bytes) -> list[str]:
    result: list[str] = []
    for child in node.children:
        if child.type == "class_heritage":
            for clause in child.children:
                if clause.type in ("extends_clause", "implements_clause"):
                    for c in clause.children:
                        if c.type in ("type_identifier", "identifier"):
                            result.append(_node_text(c, content))
    return result


def _extract_js_superclasses(node, content: bytes) -> list[str]:
    """JS class_heritage has extends keyword + identifier as direct children (no extends_clause wrapper)."""
    result: list[str] = []
    for child in node.children:
        if child.type == "class_heritage":
            for c in child.children:
                if c.type == "identifier":
                    result.append(_node_text(c, content))
    return result


def _extract_no_superclasses(_node, _content: bytes) -> list[str]:
    return []


# ---------------------------------------------------------------------------
# Body-based class collection (Python, Java, TypeScript, JavaScript)
# ---------------------------------------------------------------------------


def _collect_body_classes(
    tree, content: bytes, rel: str, abs_path: str, lang: str, config: _CkLangConfig
) -> list[_ClassInfo]:
    """Collect classes from languages with body-based class definitions."""
    classes: list[_ClassInfo] = []

    def walk(node):
        if node.type in config.class_nodes:
            name_node = node.child_by_field_name(config.class_name_field)
            if name_node is None:
                return
            name = _node_text(name_node, content)
            superclasses = config.extract_superclasses(node, content)

            body_node = None
            if config.body_field:
                body_node = node.child_by_field_name(config.body_field)

            method_count = 0
            if body_node is not None:
                for child in body_node.children:
                    if child.type in config.method_nodes:
                        method_count += 1

            # Determine kind from node type
            kind = config.kind_label
            if "interface" in node.type:
                kind = "interface"

            classes.append(_ClassInfo(
                name=name,
                file=rel,
                path=abs_path,
                line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=lang,
                kind=kind,
                superclasses=superclasses,
                scan_nodes=[body_node] if body_node is not None else [],
                method_count=method_count,
            ))

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return classes


# ---------------------------------------------------------------------------
# Go: receiver-based class collection
# ---------------------------------------------------------------------------


def _collect_go_classes(
    tree, content: bytes, rel: str, abs_path: str, lang: str
) -> list[_ClassInfo]:
    """Collect Go structs as classes, matching methods by receiver type."""
    structs: dict[str, _ClassInfo] = {}
    method_bodies: dict[str, list[Any]] = {}  # struct_name -> [body_nodes]

    def walk(node):
        # Find struct type declarations
        if node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    type_node = child.child_by_field_name("type")
                    if name_node and type_node and type_node.type == "struct_type":
                        name = _node_text(name_node, content)
                        # Extract embedded types as superclasses
                        embedded = _extract_go_embedded(type_node, content)
                        structs[name] = _ClassInfo(
                            name=name,
                            file=rel,
                            path=abs_path,
                            line=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                            language=lang,
                            kind="struct",
                            superclasses=embedded,
                            scan_nodes=[type_node],  # scan struct fields for type refs
                            method_count=0,
                        )

        # Find method declarations and group by receiver type
        if node.type == "method_declaration":
            receiver_type = _extract_go_receiver_type(node, content)
            if receiver_type:
                body = node.child_by_field_name("body")
                method_bodies.setdefault(receiver_type, [])
                if body is not None:
                    method_bodies[receiver_type].append(body)
                # Also add parameter list for type ref scanning
                params = node.child_by_field_name("parameters")
                if params is not None:
                    method_bodies[receiver_type].append(params)

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    # Merge methods into structs
    for struct_name, ci in structs.items():
        bodies = method_bodies.get(struct_name, [])
        ci.method_count = sum(1 for b in bodies if b.type == "block")
        ci.scan_nodes.extend(bodies)

    return list(structs.values())


def _extract_go_embedded(struct_type_node, content: bytes) -> list[str]:
    """Extract embedded type names from a Go struct (treated as inheritance)."""
    embedded: list[str] = []
    for child in struct_type_node.children:
        if child.type == "field_declaration_list":
            for field in child.children:
                if field.type == "field_declaration":
                    # An embedded field has no field name — just a type
                    has_name = any(c.type == "field_identifier" for c in field.children)
                    if not has_name:
                        for c in field.children:
                            if c.type == "type_identifier":
                                embedded.append(_node_text(c, content))
                            elif c.type == "pointer_type":
                                for pc in c.children:
                                    if pc.type == "type_identifier":
                                        embedded.append(_node_text(pc, content))
    return embedded


def _extract_go_receiver_type(method_node, content: bytes) -> str | None:
    """Extract the receiver type name from a Go method_declaration, stripping pointer."""
    receiver = method_node.child_by_field_name("receiver")
    if receiver is None:
        return None
    for child in receiver.children:
        if child.type == "parameter_declaration":
            type_node = child.child_by_field_name("type")
            if type_node is not None:
                if type_node.type == "pointer_type":
                    for pc in type_node.children:
                        if pc.type == "type_identifier":
                            return _node_text(pc, content)
                elif type_node.type == "type_identifier":
                    return _node_text(type_node, content)
    return None


# ---------------------------------------------------------------------------
# Rust: impl-block-based class collection
# ---------------------------------------------------------------------------


def _collect_rust_classes(
    tree, content: bytes, rel: str, abs_path: str, lang: str
) -> list[_ClassInfo]:
    """Collect Rust structs/enums/traits, matching methods via impl blocks."""
    entities: dict[str, _ClassInfo] = {}
    impl_data: dict[str, list[tuple[Any, list[str]]]] = {}  # type_name -> [(body, trait_names)]

    def walk(node):
        if node.type in ("struct_item", "enum_item", "trait_item"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node, content)
                kind = {"struct_item": "struct", "enum_item": "enum", "trait_item": "trait"}[node.type]
                body_node = node.child_by_field_name("body")
                entities[name] = _ClassInfo(
                    name=name,
                    file=rel,
                    path=abs_path,
                    line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    language=lang,
                    kind=kind,
                    superclasses=[],
                    scan_nodes=[body_node] if body_node else [],
                    method_count=0,
                )

        if node.type == "impl_item":
            type_node = node.child_by_field_name("type")
            trait_node = node.child_by_field_name("trait")
            body_node = node.child_by_field_name("body")
            if type_node:
                type_name = _node_text(type_node, content)
                trait_names = []
                if trait_node:
                    trait_names.append(_node_text(trait_node, content))
                impl_data.setdefault(type_name, []).append(
                    (body_node, trait_names)
                )

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    # Merge impl data into entities
    for type_name, impls in impl_data.items():
        ci = entities.get(type_name)
        if ci is None:
            continue
        for body_node, trait_names in impls:
            # Trait impl → add trait as superclass (coupling)
            ci.superclasses.extend(trait_names)
            if body_node is not None:
                ci.scan_nodes.append(body_node)
                # Count methods in this impl block
                for child in body_node.children:
                    if child.type == "function_item":
                        ci.method_count += 1

    return list(entities.values())


# ---------------------------------------------------------------------------
# CBO computation
# ---------------------------------------------------------------------------


def _collect_identifiers(node, content: bytes, ref_types: frozenset[str]) -> set[str]:
    """Recursively collect PascalCase identifiers from a subtree."""
    ids: set[str] = set()
    if node.type in ref_types:
        text = _node_text(node, content)
        if text and text[0].isupper():
            ids.add(text)
    for child in node.children:
        ids.update(_collect_identifiers(child, content, ref_types))
    return ids


def _compute_cbo(
    ci: _ClassInfo, content: bytes, known_classes: set[str], config: _CkLangConfig
) -> int:
    """Compute CBO by scanning scan_nodes for references to known classes."""
    coupled: set[str] = set()
    for node in ci.scan_nodes:
        coupled.update(_collect_identifiers(node, content, config.ref_node_types))
    coupled &= known_classes
    # Add superclasses that are known
    coupled.update(set(ci.superclasses) & known_classes)
    coupled.discard(ci.name)
    return len(coupled)


# ---------------------------------------------------------------------------
# DIT computation
# ---------------------------------------------------------------------------


def _compute_dit(
    name: str, parent_map: dict[str, list[str]], known: set[str]
) -> int:
    visited: set[str] = set()
    max_depth = 0

    def walk(current: str, depth: int):
        nonlocal max_depth
        if current in visited:
            return
        visited.add(current)
        if depth > max_depth:
            max_depth = depth
        for parent in parent_map.get(current, []):
            if parent in known:
                walk(parent, depth + 1)

    walk(name, 0)
    return max_depth


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------


def _interpret(cm: ClassMetrics) -> str:
    issues: list[str] = []
    if cm.cbo > 8:
        issues.append(f"high coupling (CBO={cm.cbo})")
    if cm.dit > 3:
        issues.append(f"deep inheritance (DIT={cm.dit})")
    if cm.noc > 10:
        issues.append(f"many children (NOC={cm.noc})")
    if cm.wmc > 50:
        issues.append(f"high aggregate complexity (WMC={cm.wmc})")
    if not issues:
        return (
            f"{cm.kind.title()} {cm.name}: CBO={cm.cbo}, DIT={cm.dit}, "
            f"NOC={cm.noc}, WMC={cm.wmc}. Clean."
        )
    return (
        f"{cm.kind.title()} {cm.name}: "
        + ", ".join(issues)
        + f" (CBO={cm.cbo}, DIT={cm.dit}, NOC={cm.noc}, WMC={cm.wmc})"
    )


# ---------------------------------------------------------------------------
# Language configs
# ---------------------------------------------------------------------------


_LANG_CONFIG: dict[str, _CkLangConfig] = {
    "python": _CkLangConfig(
        class_nodes=frozenset({"class_definition"}),
        class_name_field="name",
        body_field="body",
        method_nodes=frozenset({"function_definition"}),
        ref_node_types=frozenset({"identifier", "type"}),
        extract_superclasses=_extract_python_superclasses,
    ),
    "java": _CkLangConfig(
        class_nodes=frozenset({"class_declaration", "interface_declaration"}),
        class_name_field="name",
        body_field="body",
        method_nodes=frozenset({"method_declaration", "constructor_declaration"}),
        ref_node_types=frozenset({"type_identifier", "identifier"}),
        extract_superclasses=_extract_java_superclasses,
    ),
    "c_sharp": _CkLangConfig(
        class_nodes=frozenset({
            "class_declaration", "struct_declaration",
            "interface_declaration",
        }),
        class_name_field="name",
        body_field="body",
        method_nodes=frozenset({"method_declaration", "constructor_declaration"}),
        ref_node_types=frozenset({"identifier", "type_identifier"}),
        extract_superclasses=_extract_csharp_superclasses,
    ),
    "typescript": _CkLangConfig(
        class_nodes=frozenset({"class_declaration", "interface_declaration"}),
        class_name_field="name",
        body_field="body",
        method_nodes=frozenset({"method_definition", "method_signature"}),
        ref_node_types=frozenset({"type_identifier", "identifier"}),
        extract_superclasses=_extract_ts_superclasses,
    ),
    "javascript": _CkLangConfig(
        class_nodes=frozenset({"class_declaration"}),
        class_name_field="name",
        body_field="body",
        method_nodes=frozenset({"method_definition"}),
        ref_node_types=frozenset({"identifier"}),
        extract_superclasses=_extract_js_superclasses,
    ),
    "go": _CkLangConfig(
        class_nodes=frozenset(),  # Go uses receiver-based dispatch, not body walk
        class_name_field="name",
        body_field=None,
        method_nodes=frozenset({"method_declaration"}),
        ref_node_types=frozenset({"type_identifier"}),
        extract_superclasses=_extract_no_superclasses,
        kind_label="struct",
        is_receiver_based=True,
    ),
    "rust": _CkLangConfig(
        class_nodes=frozenset(),  # Rust uses impl-based dispatch
        class_name_field="name",
        body_field=None,
        method_nodes=frozenset({"function_item"}),
        ref_node_types=frozenset({"type_identifier", "identifier"}),
        extract_superclasses=_extract_no_superclasses,
        kind_label="struct",
        is_impl_based=True,
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
}


# ---------------------------------------------------------------------------
# Main kernel
# ---------------------------------------------------------------------------


def ck_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
) -> CkResult:
    """Compute Chidamber & Kemerer class metrics across a codebase."""
    errors: list[str] = []

    # Step 1: Active languages
    if languages:
        active = {lang.lower() for lang in languages} & set(_LANG_CONFIG)
    else:
        active = set(_LANG_CONFIG)
    if not active:
        return CkResult(
            classes=[], files_searched=0, classes_analyzed=0, languages={},
            errors=[f"No supported languages. Supported: {sorted(_LANG_CONFIG)}"],
        )

    # Step 2: File discovery
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

    # Step 3: Enumerate classes across all files
    all_classes: list[_ClassInfo] = []
    file_contents: dict[str, bytes] = {}
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
        file_contents[str(fp)] = content

        rel = _relative_path(root, fp)
        if config.is_receiver_based:
            classes_in_file = _collect_go_classes(tree, content, rel, str(fp), lang)
        elif config.is_impl_based:
            classes_in_file = _collect_rust_classes(tree, content, rel, str(fp), lang)
        else:
            classes_in_file = _collect_body_classes(tree, content, rel, str(fp), lang, config)

        all_classes.extend(classes_in_file)
        if classes_in_file:
            language_counts[lang] = language_counts.get(lang, 0) + len(classes_in_file)

    if not all_classes:
        return CkResult(
            classes=[], files_searched=find_result.total_found,
            classes_analyzed=0, languages=language_counts, errors=errors,
        )

    # Step 4: Build class registry + inheritance maps
    known_class_names: set[str] = {ci.name for ci in all_classes}
    parent_map: dict[str, list[str]] = {}
    children_map: dict[str, list[str]] = {}
    for ci in all_classes:
        parent_map.setdefault(ci.name, []).extend(ci.superclasses)
        for parent in ci.superclasses:
            children_map.setdefault(parent, []).append(ci.name)

    # Step 5: WMC via ccx_kernel composition
    ccx_result = ccx_kernel(
        root=root,
        languages=list(active) if languages else None,
        globs=globs, excludes=excludes,
        hidden=hidden, no_ignore=no_ignore, min_ccx=1,
    )
    errors.extend(f"ccx: {e}" for e in ccx_result.errors)

    wmc_by_class: dict[tuple[str, str, int], int] = {}
    classes_by_file: dict[str, list[_ClassInfo]] = {}
    for ci in all_classes:
        classes_by_file.setdefault(ci.file, []).append(ci)
    for file_classes in classes_by_file.values():
        file_classes.sort(key=lambda c: (c.end_line - c.line))

    for fn in ccx_result.functions:
        for ci in classes_by_file.get(fn.file, []):
            if ci.line <= fn.line <= ci.end_line:
                key = (ci.file, ci.name, ci.line)
                wmc_by_class[key] = wmc_by_class.get(key, 0) + fn.ccx
                break

    # Step 6: Build ClassMetrics
    class_metrics: list[ClassMetrics] = []
    for ci in all_classes:
        content = file_contents.get(ci.path, b"")
        config = _LANG_CONFIG[ci.language]

        cbo = _compute_cbo(ci, content, known_class_names, config)
        dit = _compute_dit(ci.name, parent_map, known_class_names)
        noc = len(children_map.get(ci.name, []))
        wmc = wmc_by_class.get((ci.file, ci.name, ci.line), 0)

        cm = ClassMetrics(
            name=ci.name, file=ci.file, path=ci.path,
            line=ci.line, end_line=ci.end_line,
            language=ci.language, kind=ci.kind,
            cbo=cbo, dit=dit, noc=noc, wmc=wmc,
            method_count=ci.method_count,
            superclasses=ci.superclasses,
            interpretation="",
        )
        cm.interpretation = _interpret(cm)
        class_metrics.append(cm)

    # Step 7: Sort + truncate
    class_metrics.sort(key=lambda c: (-c.cbo, -c.wmc, c.name))
    truncated = False
    if max_results is not None and len(class_metrics) > max_results:
        class_metrics = class_metrics[:max_results]
        truncated = True

    return CkResult(
        classes=class_metrics,
        files_searched=find_result.total_found,
        classes_analyzed=len(class_metrics),
        languages=language_counts,
        errors=errors,
        truncated=truncated,
    )
