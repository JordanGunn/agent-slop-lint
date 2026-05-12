"""``Language`` — the base grammar contract.

The abstract base class every concrete grammar implementation
satisfies. Cannot be instantiated, but all methods are classmethods —
grammar dispatch never requires construction.

Concrete grammars declare:
  - ``id`` — the language identifier (e.g. "python"); also the
    tree-sitter package suffix (``tree_sitter_python``).
  - ``callable()`` — the set of tree-sitter node types that define
    callables in this language.
  - Optionally, overrides for ``identifiers()``, ``extract_name()``,
    ``extract_parameters()`` when the language's tree-sitter conventions
    differ from the defaults.

The actual AST walking lives in ``Tree`` — grammars are tabular
metadata + extractor helpers, never iterators or walkers.

See ``docs/planning/language.md`` for the locked design.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from slop._ast.treesitter import load_language

if TYPE_CHECKING:
    from slop.tree.records import Parameter


class Language(ABC):
    """Base grammar contract — the interface every concrete grammar satisfies.

    Concrete grammars declare ``id`` (the language identifier used by
    views' ``where(language=...)`` filter AND as the tree-sitter
    package suffix) and ``callable()`` (the node types this language
    uses to define callables).
    """

    id: ClassVar[str]

    @classmethod
    def grammar(cls) -> Any:
        """The tree-sitter ``Language`` object for this grammar.

        Lazily loaded + cached by ``_ast.treesitter._LANGUAGE_CACHE``
        on first call. Calling repeatedly is O(1).
        """
        return load_language(cls.id)

    @classmethod
    @abstractmethod
    def callable(cls) -> frozenset[str]:
        """All tree-sitter node types that define callables in this language.

        The semantic discrimination between functions and methods is
        handled by ``Procedural.functions()`` / ``ObjectOriented.methods()``
        (which default to ``cls.callable()``) and by the walk's
        class-context tracking.
        """

    @classmethod
    def identifiers(cls) -> frozenset[str]:
        """Tree-sitter node types that represent identifier tokens.

        Default ``{"identifier"}`` works for most languages. Grammars
        with field/property/type variants (Go, Cpp field_identifier;
        JS property_identifier; TS type_identifier) override this to
        widen the set.
        """
        return frozenset({"identifier"})

    @classmethod
    def extract_name(cls, node: Any, content: bytes) -> str:
        """Extract the name of a named node (function, class, etc.).

        Default leans on tree-sitter convention: ``child_by_field_name("name")``.
        Languages that don't follow this convention (C declarator chains,
        C++ qualified_identifier, Ruby positional def, Julia short-form)
        override this classmethod.

        Returns ``"<anonymous>"`` when no name can be extracted.
        """
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return "<anonymous>"
        return content[name_node.start_byte:name_node.end_byte].decode(
            "utf-8", errors="replace",
        )

    @classmethod
    def extract_parameters(cls, node: Any, content: bytes) -> tuple[Parameter, ...]:
        """Extract parameters from a callable definition node.

        Default walks the ``parameters`` field and processes each child
        node by type (identifier, typed_parameter, default_parameter,
        list_splat_pattern, dictionary_splat_pattern). Languages whose
        parameter syntax differs significantly override this method.
        """
        from slop.tree.records import Parameter

        params_node = node.child_by_field_name("parameters")
        if params_node is None:
            return ()
        out: list[Parameter] = []
        position = 0
        for child in params_node.children:
            ctype = child.type
            if ctype in ("(", ")", ",", "*", "**", "/", "=", "lambda"):
                continue
            param_name, annotation = _default_parameter_parts(child, content)
            if param_name is None:
                continue
            out.append(Parameter(name=param_name, position=position, annotation=annotation))
            position += 1
        return tuple(out)


def _default_parameter_parts(node: Any, content: bytes) -> tuple[str | None, str | None]:
    """Default (name, annotation) extraction for one parameter node.

    Handles the common tree-sitter parameter shapes:
      - identifier
      - typed_parameter / typed_default_parameter
      - default_parameter
      - list_splat_pattern (*args) / dictionary_splat_pattern (**kwargs)
    """
    ntype = node.type
    if ntype == "identifier":
        return (content[node.start_byte:node.end_byte].decode("utf-8", errors="replace"), None)
    if ntype in ("typed_parameter", "typed_default_parameter"):
        name = None
        for c in node.children:
            if c.type == "identifier":
                name = content[c.start_byte:c.end_byte].decode("utf-8", errors="replace")
                break
        type_node = node.child_by_field_name("type")
        annotation = None
        if type_node is not None:
            annotation = content[type_node.start_byte:type_node.end_byte].decode(
                "utf-8", errors="replace",
            ).strip()
        return (name, annotation)
    if ntype == "default_parameter":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return (
                content[name_node.start_byte:name_node.end_byte].decode(
                    "utf-8", errors="replace",
                ),
                None,
            )
        return (None, None)
    if ntype in ("list_splat_pattern", "dictionary_splat_pattern"):
        for c in node.children:
            if c.type == "identifier":
                prefix = "*" if ntype == "list_splat_pattern" else "**"
                return (
                    prefix
                    + content[c.start_byte:c.end_byte].decode("utf-8", errors="replace"),
                    None,
                )
        return (None, None)
    return (None, None)
