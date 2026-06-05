"""``MultiPurpose`` — the diamond: grammars emitting both classes and free functions."""
from __future__ import annotations

from abc import ABC
from typing import ClassVar

from .base import Paradigm
from .objectoriented import ObjectOriented
from .procedural import Procedural


class MultiPurpose(ObjectOriented, Procedural, ABC):
    """Diamond marker — a grammar emitting both classes and free functions."""

    PARADIGM: ClassVar[Paradigm] = Paradigm.MULTI_PURPOSE
