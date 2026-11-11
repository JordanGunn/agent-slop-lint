"""The boundary of a source: what it is given and what it yields."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ...dispatch import Report
from ..contract import Residue


@dataclass(frozen=True)
class Analysis:
    """The deterministic analysis of a project that a source may draw on."""

    root: Path
    report: Report


class Source(ABC):
    #: The source's name, recorded where it matters (``finding``, later ``survey``).
    name: ClassVar[str]

    @abstractmethod
    def residue(self, analysis: Analysis) -> Iterator[Residue]:
        """The items of ``analysis`` that need judgement, one residue each."""
