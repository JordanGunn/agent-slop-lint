"""``Scope`` — tree-sitter node types that define class-like scopes.

Classes, structs, interfaces, records, traits, impl blocks, modules.
The criterion is "named scope containing methods or fields" — what a
grammar's ``classes()`` classmethod would return.

Note: ``slop.tree.records`` also exports a ``Scope`` dataclass.
Files using both will alias one of them at import time.
"""
from __future__ import annotations

from enum import StrEnum


class Scope(StrEnum):
    CLASS_DEFINITION = "class_definition"
    CLASS_DECLARATION = "class_declaration"
    CLASS_SPECIFIER = "class_specifier"
    STRUCT_DECLARATION = "struct_declaration"
    STRUCT_SPECIFIER = "struct_specifier"
    ENUM_ITEM = "enum_item"
    STRUCT_ITEM = "struct_item"
    INTERFACE_DECLARATION = "interface_declaration"
    ABSTRACT_CLASS_DECLARATION = "abstract_class_declaration"
    RECORD_DECLARATION = "record_declaration"
    TRAIT_ITEM = "trait_item"
    IMPL_ITEM = "impl_item"
    TYPE_DECLARATION = "type_declaration"
    MODULE = "module"
    CLASS = "class"
