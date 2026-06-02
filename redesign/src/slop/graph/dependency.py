"""DependencyGraph — directed import/include/require/use graph over components.

Built first among the derived graphs because it grounds on import extraction we
already trust (legacy: structure/imports.py + deps). Primary node type is
Module; Package/Realm graphs are derived by contracting Module nodes upward.

Interfaces only — implementation is build step 6.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from ..scope.identity import ComponentId, Span
from ..scope.metrics import DependencyCycle


@dataclass(frozen=True)
class DependencyEdge:
    """A directed dependency between two components, evidence preserved.

    ``to`` may be unresolved (an external dependency or bare specifier string),
    so the edge records ``resolved`` and the ``raw_specifier`` rather than
    forcing false precision.
    """

    from_: ComponentId
    to: ComponentId | None
    kind: str               # import | include | require | use | build | reference
    raw_specifier: str
    source: Span
    resolved: bool


class DependencyGraph(ABC):
    """Directed graph of dependency edges. Node identity is ``ComponentId``;
    Package/Realm/Corpus graphs derive by contracting Module nodes upward.
    """

    @abstractmethod
    def edges(self) -> Sequence[DependencyEdge]:
        """All dependency edges in the graph."""
        ...

    @abstractmethod
    def afferent(self, node: ComponentId) -> int:
        """Ca — count of components that depend on ``node``."""
        ...

    @abstractmethod
    def efferent(self, node: ComponentId) -> int:
        """Ce — count of components ``node`` depends on."""
        ...

    @abstractmethod
    def cycles(self) -> Sequence[DependencyCycle]:
        """Strongly-connected components with >1 node (import cycles, Tarjan SCC)."""
        ...
