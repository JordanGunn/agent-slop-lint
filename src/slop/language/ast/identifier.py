"""``Identifier`` — tree-sitter node types representing names.

Plain identifiers, qualified identifiers (e.g. C++ ``Foo::bar``),
field/property/type-specific identifier variants, and the
operator/destructor name nodes used in C++ operator overloads and
destructors. Anything that a name-extraction routine treats as "the
name lives here" belongs in this enum.
"""
from __future__ import annotations

from enum import StrEnum


class Identifier(StrEnum):
    IDENTIFIER = "identifier"
    FIELD_IDENTIFIER = "field_identifier"
    PROPERTY_IDENTIFIER = "property_identifier"
    TYPE_IDENTIFIER = "type_identifier"
    QUALIFIED_IDENTIFIER = "qualified_identifier"
    OPERATOR = "operator"
    OPERATOR_NAME = "operator_name"
    DESTRUCTOR_NAME = "destructor_name"
