"""Carving — turn a filesystem root into the component hierarchy.

``scan_corpus`` discovers source files, parses them, and carves
Corpus → Realm → Package → Module → Class → Callable. Parenting is done by
construction (owner back-references set as the tree is assembled) — there is no
post-hoc re-parenting hook. Python-shaped first; broadens via the grammar
registry.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..component.identity import CallableKind, ComponentId, ComponentKind, Extent, Span
from ..language import GRAMMARS_BY_ID
from ..language.paradigms import ObjectOriented
from ..parse import detect_language, parse_file
from . import components as C

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache"}
_LAMBDA_TYPES = {"lambda", "arrow_function", "lambda_expression", "func_literal", "function_expression"}
_METHOD_ONLY_TYPES = {"method_declaration", "method_definition", "singleton_method"}


def scan_corpus(root: Path, config: Any) -> C.Corpus:
    """Build a Corpus from ``root``. One Realm per detected language; modules
    grouped into packages by directory."""
    root = Path(root)
    files_by_lang: dict[str, list[Path]] = {}
    for path in _iter_source_files(root):
        lang = detect_language(path)
        if lang is None or lang not in GRAMMARS_BY_ID:
            continue
        files_by_lang.setdefault(lang, []).append(path)

    realms: list[C.Realm] = []
    for lang, paths in sorted(files_by_lang.items()):
        grammar = GRAMMARS_BY_ID[lang]
        realm = _carve_realm(root, lang, grammar, paths)
        if realm is not None:
            realms.append(realm)

    corpus = C.Corpus(
        root=root, config=config,
        id=ComponentId(ComponentKind.CORPUS, root.name or "<root>", ()),
        name=root.name or "<root>", owner=None,
        extent=_union_extent(realms), files=_union_files(realms),
        children=realms,
    )
    for r in realms:
        r._owner = corpus
    return corpus


def _carve_realm(root: Path, lang: str, grammar: type, paths: list[Path]) -> C.Realm | None:
    # Group modules into packages by directory (one Package per dir).
    by_dir: dict[Path, list[C.Module]] = {}
    for path in sorted(paths):
        module = _carve_module(path, grammar)
        if module is not None:
            by_dir.setdefault(path.parent, []).append(module)
    if not by_dir:
        return None

    packages: list[C.Package] = []
    for directory, modules in sorted(by_dir.items()):
        pkg_name = _rel_name(directory, root)
        pkg = C.Package(
            path=directory,
            id=ComponentId(ComponentKind.PACKAGE, pkg_name, ()),
            name=directory.name or pkg_name, owner=None,
            extent=_union_extent(modules), files=_union_files(modules),
            children=modules,
        )
        for m in modules:
            m._owner = pkg
        packages.append(pkg)

    realm = C.Realm(
        root=root, grammar=grammar, language=lang,
        id=ComponentId(ComponentKind.REALM, lang, ()),
        name=lang, owner=None,
        extent=_union_extent(packages), files=_union_files(packages),
        children=packages,
    )
    for p in packages:
        p._owner = realm
    return realm


def _carve_module(path: Path, grammar: type) -> C.Module | None:
    parsed = parse_file(path, grammar.id)
    if parsed is None:
        return None
    tree, content = parsed
    root_node = tree.root_node
    qualname = path.stem if path.stem != "__init__" else (path.parent.name or "<root>")
    span = Span(str(path), 0, len(content))

    children = _carve_decls(
        root_node, grammar=grammar, content=content, path=path,
        parts=(qualname,), in_class=False,
    )
    module = C.Module(
        id=ComponentId(ComponentKind.MODULE, qualname, (span,)),
        name=qualname, owner=None, extent=Extent((span,)), files=(path,),
        children=children, node=root_node, content=content, grammar=grammar,
    )
    for ch in children:
        ch._owner = module
    return module


def _carve_decls(
    node: Any, *, grammar: type, content: bytes, path: Path,
    parts: tuple[str, ...], in_class: bool,
) -> tuple[Any, ...]:
    """Direct declaration components within ``node`` (descending through
    non-declaration nodes, stopping at class/callable nodes)."""
    is_oo = issubclass(grammar, ObjectOriented)
    class_types = grammar.classes() if is_oo else frozenset()
    callable_types = grammar.callable()
    out: list[Any] = []
    for child in node.children:
        if child.type in class_types:
            out.append(_make_class(child, grammar, content, path, parts))
        elif child.type in callable_types:
            out.append(_make_callable(child, grammar, content, path, parts, in_class))
        else:
            out.extend(_carve_decls(
                child, grammar=grammar, content=content, path=path,
                parts=parts, in_class=in_class,
            ))
    return tuple(out)


def _make_class(node: Any, grammar: type, content: bytes, path: Path, parts: tuple[str, ...]) -> C.Class:
    name = grammar.extract_name(node, content) or "<anonymous>"
    qn = ".".join((*parts, name))
    span = Span(str(path), node.start_byte, node.end_byte)
    body = node.child_by_field_name("body") or node
    children = _carve_decls(
        body, grammar=grammar, content=content, path=path,
        parts=(*parts, name), in_class=True,
    )
    is_abs = grammar.is_abstract_scope(node, content)
    klass = C.Class(
        is_abstract=bool(is_abs), bases=tuple(grammar.extract_superclasses(node, content)),
        properties=(),
        id=ComponentId(ComponentKind.CLASS, qn, (span,)),
        name=name, owner=None, extent=Extent((span,)), files=(path,),
        children=children, node=node, content=content, grammar=grammar,
    )
    for ch in children:
        ch._owner = klass
    return klass


def _make_callable(
    node: Any, grammar: type, content: bytes, path: Path,
    parts: tuple[str, ...], in_class: bool,
) -> C.Callable:
    name = grammar.extract_name(node, content) or "<anonymous>"
    qn = ".".join((*parts, name))
    span = Span(str(path), node.start_byte, node.end_byte)
    body = node.child_by_field_name("body") or node
    # Nested callables become child components; nested classes too (rare).
    children = _carve_decls(
        body, grammar=grammar, content=content, path=path,
        parts=(*parts, name), in_class=False,
    )
    params = tuple(n for n, _anno in grammar.extract_parameters(node, content))
    callable_ = C.Callable(
        kind=_callable_kind(node.type, in_class), parameters=params,
        id=ComponentId(ComponentKind.CALLABLE, qn, (span,)),
        name=name, owner=None, extent=Extent((span,)), files=(path,),
        children=children, node=node, content=content, grammar=grammar,
    )
    for ch in children:
        ch._owner = callable_
    return callable_


def _callable_kind(node_type: str, in_class: bool) -> CallableKind:
    if node_type in _LAMBDA_TYPES:
        return CallableKind.LAMBDA
    if node_type in _METHOD_ONLY_TYPES or in_class:
        return CallableKind.METHOD
    return CallableKind.FUNCTION


# ---- discovery + aggregate-extent helpers --------------------------------

def _iter_source_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        yield path


def _rel_name(directory: Path, root: Path) -> str:
    try:
        rel = directory.resolve().relative_to(root.resolve())
        return rel.as_posix() or (root.name or "<root>")
    except ValueError:
        return directory.name or "<root>"


def _union_extent(components) -> Extent:
    spans: list[Span] = []
    for comp in components:
        spans.extend(comp.extent.spans)
    return Extent(tuple(spans))


def _union_files(components) -> tuple[Path, ...]:
    seen: list[Path] = []
    for comp in components:
        for f in comp.files:
            if f not in seen:
                seen.append(f)
    return tuple(seen)
