"""The boundary of a source: what it is given and what it yields."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from ...dispatch import Report
from ...identity import ScopeId
from ..contract import Residue


@dataclass(frozen=True)
class Analysis:
    """The deterministic analysis of a project that a source may draw on."""

    #: The project root: the directory holding the config, else the scan root. Finding paths and
    #: the ledger are relative to it, so they do not depend on which directory was scanned.
    root: Path
    report: Report
    #: The scope tree the report was made from; a source reads definitions' extents from it.
    corpus: Any


class Source(ABC):
    #: The source's name, recorded where it matters (``finding``, later ``survey``).
    name: ClassVar[str]

    @abstractmethod
    def residue(self, analysis: Analysis) -> Iterator[Residue]:
        """The items of ``analysis`` that need judgement, one residue each."""


def scopes(corpus: Any) -> dict[ScopeId, Any]:
    """Every scope of ``corpus`` by its id."""
    found: dict[ScopeId, Any] = {}
    stack = [corpus]
    while stack:
        component = stack.pop()
        found[component.id] = component
        stack.extend(component.children())
    return found
