"""Instance-member facts JavaScript and TypeScript share: a method reaches its own instance
through ``this``, spelled ``this.member``; ``static`` methods have no instance."""
from __future__ import annotations

from typing import Any

from ..paradigm.base import MemberAccess


class EcmaScriptMembers:
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
