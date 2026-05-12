"""Julia grammar — procedural; multimethods don't bind receivers."""
from __future__ import annotations

from typing import ClassVar

from ..procedural import Procedural


class Julia(Procedural):
    id: ClassVar[str] = "julia"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "arrow_function_expression"})
