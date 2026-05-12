"""Python grammar — class-and-function-emitting, multi-paradigm."""
from __future__ import annotations

from typing import ClassVar

from ..multipurpose import MultiPurpose


class Python(MultiPurpose):
    id: ClassVar[str] = "python"

    @classmethod
    def callable(cls) -> frozenset[str]:
        return frozenset({"function_definition", "async_function_definition", "lambda"})

    @classmethod
    def classes(cls) -> frozenset[str]:
        return frozenset({"class_definition"})

    @classmethod
    def methods(cls) -> frozenset[str]:
        # Lambdas can't be methods in Python (no `def` inside class via lambda).
        return frozenset({"function_definition", "async_function_definition"})
