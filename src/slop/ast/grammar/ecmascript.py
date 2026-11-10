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
