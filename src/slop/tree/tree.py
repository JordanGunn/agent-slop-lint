"""Tree orchestrator — owns the walk, builds the views.

``Tree`` walks the file tree once, parses each file via tree-sitter
(using ``_ast.parse_file``), and dispatches AST traversal to grammar
classmethod metadata. The walk produces ``ParseResult``s; the views
are materialised lazily on first property access.

One Tree per repo. Language is a filter axis on the views; never an
axis on Tree. Immutable post-scan.

Renamed from ``Tree`` in the v2 decomposition. The class name
matches the module + package, and reflects what the thing actually
is — a parsed AST forest.

See ``docs/planning/codebase.md`` for the locked design.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from slop._ast.treesitter import detect_language, parse_file
from slop._fs.find import find_kernel
from slop.language import Language
from slop.language.grammars import DEFAULT_GRAMMARS
from slop.lexicon.view import Lexicon
from slop.structure.view import Structure

from .records import (
    Callable,
    CallableKind,
    Occurrence,
    ParseResult,
    Scope,
    ScopeKind,
)


class Tree:
    """The corpus orchestrator.

    Constructed with a root path and optional grammars / excludes.
    ``scan()`` walks the tree, parses every recognised file, and
    populates the internal parse list. Views are accessed via
    properties (lazy on first access).
    """

    def __init__(
        self,
        root: Path,
        *,
        grammars: Mapping[str, type[Language]] | None = None,
        excludes: Sequence[str] = (),
    ) -> None:
        self.root = Path(root)
        self.grammars: Mapping[str, type[Language]] = (
            grammars if grammars is not None else DEFAULT_GRAMMARS
        )
        self.excludes = tuple(excludes)
        self._parses: list[ParseResult] = []
        self._scanned = False
        self._structure: Structure | None = None
        self._lexicon: Lexicon | None = None
        self._languages_detected: list[str] = []
        self._scan_errors: list[str] = []

    # ---- scan --------------------------------------------------------

    def scan(self) -> None:
        """One fd walk; parse each file via tree-sitter; build per-file ParseResults."""
        if self._scanned:
            return

        extensions = sorted(set(self.grammars.keys()))
        globs = [f"**/*{ext}" for ext in extensions]

        find_result = find_kernel(
            root=self.root,
            globs=globs,
            excludes=list(self.excludes) if self.excludes else None,
        )

        seen_languages: set[str] = set()
        for entry in find_result.entries:
            if entry.type != "file":
                continue
            file_path = self.root / entry.path
            grammar_cls = self._grammar_for(file_path)
            if grammar_cls is None:
                continue
            parse = self._parse_file(file_path, grammar_cls)
            if parse is None:
                continue
            self._parses.append(parse)
            seen_languages.add(parse.language)

        self._languages_detected = sorted(seen_languages)
        self._scanned = True

    def _grammar_for(self, path: Path) -> type[Language] | None:
        """Look up the grammar class for a file by extension."""
        return self.grammars.get(path.suffix.lower())

    # ---- per-file walk -----------------------------------------------

    def _parse_file(self, path: Path, grammar: type[Language]) -> ParseResult | None:
        """Parse one file + walk the tree, producing one ParseResult."""
        parsed = parse_file(path, grammar.id)
        if parsed is None:
            self._scan_errors.append(f"{path}: parse failed")
            return None
        tree, content = parsed

        scopes: list[Scope] = []
        callables: list[Callable] = []
        occurrences: list[Occurrence] = []
        callable_nodes: dict[str, Any] = {}
        scope_nodes: dict[str, Any] = {}

        # File-level scope (single-file-as-module convention).
        file_qualname = path.stem if path.stem != "__init__" else (path.parent.name or "<root>")
        scopes.append(
            Scope(
                qualname=file_qualname,
                kind=ScopeKind.FILE,
                path=path,
                line=1,
                end_line=tree.root_node.end_point[0] + 1,
                parent=None,
            )
        )

        # Compute paradigm flags once per grammar — drives method-vs-function tagging.
        from slop.language.objectoriented import ObjectOriented
        is_oo = issubclass(grammar, ObjectOriented)

        # Pre-fetch node-type sets (frozensets — repeated membership tests).
        callable_types = grammar.callable()
        class_types = grammar.classes() if is_oo else frozenset()
        method_types = grammar.methods() if is_oo else frozenset()
        identifier_types = grammar.identifiers()

        self._walk(
            node=tree.root_node,
            content=content,
            grammar=grammar,
            path=path,
            qualname_parts=(file_qualname,),
            in_class=False,
            callable_types=callable_types,
            class_types=class_types,
            method_types=method_types,
            identifier_types=identifier_types,
            scopes=scopes,
            callables=callables,
            occurrences=occurrences,
            callable_nodes=callable_nodes,
            scope_nodes=scope_nodes,
        )

        return ParseResult(
            path=path,
            language=grammar.id,
            scopes=tuple(scopes),
            callables=tuple(callables),
            occurrences=tuple(occurrences),
            callable_nodes=callable_nodes,
            scope_nodes=scope_nodes,
            content=content,
        )

    def _walk(
        self,
        *,
        node: Any,
        content: bytes,
        grammar: type[Language],
        path: Path,
        qualname_parts: tuple[str, ...],
        in_class: bool,
        callable_types: frozenset[str],
        class_types: frozenset[str],
        method_types: frozenset[str],
        identifier_types: frozenset[str],
        scopes: list[Scope],
        callables: list[Callable],
        occurrences: list[Occurrence],
        callable_nodes: dict[str, Any],
        scope_nodes: dict[str, Any],
    ) -> None:
        """Invariant DFS — uses grammar classmethods for per-language tests."""
        ntype = node.type
        new_parts = qualname_parts
        new_in_class = in_class

        if ntype in class_types:
            name = grammar.extract_name(node, content) or "<anonymous>"
            qn = ".".join((*qualname_parts, name)) if name else ".".join(qualname_parts)
            scopes.append(
                Scope(
                    qualname=qn,
                    kind=ScopeKind.CLASS,
                    path=path,
                    line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parent=".".join(qualname_parts) if qualname_parts else None,
                )
            )
            scope_nodes[qn] = node
            new_parts = (*qualname_parts, name)
            new_in_class = True

        elif ntype in callable_types:
            name = grammar.extract_name(node, content) or "<anonymous>"
            qn = ".".join((*qualname_parts, name)) if name else ".".join(qualname_parts)
            kind = _callable_kind(ntype, in_class, method_types)
            params = grammar.extract_parameters(node, content)
            callables.append(
                Callable(
                    qualname=qn,
                    kind=kind,
                    path=path,
                    line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parent=".".join(qualname_parts) if qualname_parts else None,
                    parameters=params,
                )
            )
            callable_nodes[qn] = node
            new_parts = (*qualname_parts, name) if name else qualname_parts
            new_in_class = False  # don't propagate in_class into a nested callable

        elif ntype in identifier_types:
            text = content[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            occurrences.append(
                Occurrence(
                    token=text,
                    path=path,
                    line=node.start_point[0] + 1,
                    col=node.start_point[1],
                    scope=".".join(qualname_parts) if qualname_parts else None,
                    callable=None,
                    kind="identifier",
                )
            )

        for child in node.children:
            self._walk(
                node=child,
                content=content,
                grammar=grammar,
                path=path,
                qualname_parts=new_parts,
                in_class=new_in_class,
                callable_types=callable_types,
                class_types=class_types,
                method_types=method_types,
                identifier_types=identifier_types,
                scopes=scopes,
                callables=callables,
                occurrences=occurrences,
                callable_nodes=callable_nodes,
                scope_nodes=scope_nodes,
            )

    # ---- views -------------------------------------------------------

    @property
    def structure(self) -> Structure:
        if not self._scanned:
            raise RuntimeError("Tree.scan() has not been called")
        if self._structure is None:
            self._structure = Structure(self._parses)
        return self._structure

    @property
    def lexicon(self) -> Lexicon:
        if not self._scanned:
            raise RuntimeError("Tree.scan() has not been called")
        if self._lexicon is None:
            self._lexicon = Lexicon(self._parses)
        return self._lexicon

    @property
    def languages_detected(self) -> Sequence[str]:
        if not self._scanned:
            raise RuntimeError("Tree.scan() has not been called")
        return tuple(self._languages_detected)


def _callable_kind(
    node_type: str,
    in_class: bool,
    method_types: frozenset[str],  # noqa: ARG001  — kept for caller compat
) -> CallableKind:
    """Determine the kind tag for a callable node.

    Priority:
      1. Anonymous-shape node types are LAMBDA regardless of context.
      2. Syntactically method-only node types (Go ``method_declaration``,
         JS ``method_definition``, Ruby ``singleton_method``) — always
         METHOD; tree-sitter has already discriminated by node type.
      3. Context-based: ``in_class`` true → METHOD; else FUNCTION.

    ``method_types`` is intentionally unused here. Earlier versions
    tried to use it as a discriminator, but in languages where the same
    node type serves both free functions and methods (Python, C++, Rust,
    Ruby method), ``method_types`` overlaps with ``functions()`` —
    falsely tagging free functions as METHOD. Context is the only
    reliable signal for shared node types.
    """
    if node_type in (
        "lambda", "arrow_function", "arrow_function_expression",
        "lambda_expression", "func_literal", "function_expression",
    ):
        return CallableKind.LAMBDA
    if node_type in ("method_declaration", "method_definition", "singleton_method"):
        return CallableKind.METHOD
    if in_class:
        return CallableKind.METHOD
    return CallableKind.FUNCTION
