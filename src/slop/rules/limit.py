"""Limit: a rule that compares one measure with a ``limit`` option at one altitude.

Most rules are exactly this: measure something about a component, and report it when the
measure is over the configured limit. A subclass names the altitude and the default limit,
says how to measure (``measure``), and how to word the violation (``describe``).
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar

from ..config import RuleConfig
from ..metrics.structural.view import Structure
from ..rule import Rule
from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..violation import Violation


class Limit(Rule):
    altitude: ClassVar[ScopeKind]
    default_limit: ClassVar[int | float]
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "altitude" in cls.__dict__:
            cls.altitudes = frozenset({cls.altitude})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, enabled=True,
                          options={"limit": cls.default_limit})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Violation]:
        limit = config.option("limit")
        view = Structure.over(component)
        value = self.measure(view)
        if value is not None and value > limit:
            yield Violation.at(component, self.name, self.describe(component, value, limit, view),
                               value=value, threshold=limit)

    def measure(self, view: Structure) -> float | None:
        """The measure for the component under ``view``, or None when it does not apply."""
        raise NotImplementedError

    def describe(self, component: Scope, value: Any, limit: float, view: Structure) -> str:
        """One factual sentence naming the component, the measure and the limit."""
        raise NotImplementedError
