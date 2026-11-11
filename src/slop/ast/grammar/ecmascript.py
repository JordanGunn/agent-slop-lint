"""Facts JavaScript and TypeScript share: callable, loop and decision node types, import
queries, and instance members (a method reaches its own instance through ``this.member``;
``static`` methods have no instance). TypeScript adds syntax; it does not redeclare these."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..paradigm.base import MemberAccess, ModuleIndex, distinct


class EcmaScript:
    @classmethod
    def member_access(cls) -> MemberAccess | None:
        return MemberAccess("member_expression", "object", "property")

    @classmethod
    def instance_receiver(cls, method: Any, content: bytes) -> str | None:
        del content
        return None if any(c.type == "static" for c in method.children) else "this"

    @classmethod
    def constructor_names(cls) -> frozenset[str]:
        return frozenset({"constructor"})

    @classmethod
    def class_fields(cls, node: Any, content: bytes) -> tuple[str, ...]:
        """Fields in the class body: TypeScript's ``public_field_definition`` (name in
        ``name``) and JavaScript's ``field_definition`` (name in ``property``)."""
        body = node.child_by_field_name("body")
        field_of = {"public_field_definition": "name", "field_definition": "property"}
        names: list[str] = []
        for member in body.named_children if body is not None else ():
            key = field_of.get(member.type)
            target = member.child_by_field_name(key) if key else None
            if target is not None:
                names.append(content[target.start_byte:target.end_byte].decode())
        return tuple(names)

    @classmethod
    def assignment_nodes(cls) -> frozenset[str]:
        # ``this.v += 1`` can only update a member that exists, so it declares nothing.
        return frozenset({"assignment_expression"})

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "function_expression", "arrow_function",
                          "method_definition", "generator_function_declaration"})

    @classmethod
    def functions(cls) -> frozenset[str]:
        return frozenset({"function_declaration", "function_expression",
                          "arrow_function", "generator_function_declaration"})

    @classmethod
    def decision_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement", "switch_case", "catch_clause",
                          "ternary_expression"})

    @classmethod
    def nesting_nodes(cls) -> frozenset[str]:
        return frozenset({"if_statement", "for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement", "switch_statement", "catch_clause",
                          "ternary_expression"})

    @classmethod
    def boolean_op_operators(cls) -> frozenset[str] | None:
        return frozenset({"&&", "||", "??"})

    @classmethod
    def loop_nodes(cls) -> frozenset[str]:
        return frozenset({"for_statement", "for_in_statement", "for_of_statement",
                          "while_statement", "do_statement"})

    @classmethod
    def import_queries(cls) -> tuple[tuple[str, str], ...]:
        return (
            ("(import_statement source: (string (string_fragment) @module))", "esm"),
            ("((call_expression function: (identifier) @fn"
             " arguments: (arguments (string (string_fragment) @module)))"
             " (#eq? @fn \"require\"))", "require"),
        )

    @classmethod
    def resolve_import(cls, decl: Any, importer: Path, index: ModuleIndex) -> tuple[Any, ...]:
        """``./`` and ``../`` name a file beside the importer: as written, without its extension
        (``./x.js`` for ``x.ts``), or a directory's ``index``. Bare specifiers (packages, path
        aliases) take the default."""
        if not decl.specifier.startswith(("./", "../")):
            return super().resolve_import(decl, importer, index)
        place = importer.parent / decl.specifier
        return distinct([index.at(place) or index.at(place.with_suffix("")) or index.at(place / "index")])
