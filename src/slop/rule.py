"""Rule contract.

A rule **declares** the altitude(s) it is defined at (``altitudes``); the dispatcher
(``slop.dispatch``) walks the component tree and calls the rule at every component of
that altitude. A rule never walks the corpus itself, so it cannot run where it is
undefined, and the dispatcher reports a rule that examined nothing instead of letting it
pass as clean.

A rule is a limit on a measure. It does not compute the measure: that lives on a metric
view (``Structure.over(component)``), which ``find``, ``shape`` and ``lexicon`` read too.
Keeping the measure out of the rule is what lets one number serve both a question ("what
is this class's cohesion?") and a check ("cohesion is over 2").
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import ClassVar

from .config import RuleConfig
from .scope.base import Scope
from .scope.identity import ScopeKind
from .violation import Violation


class Rule(ABC):
    #: the rule's name (``cyclomatic-complexity``): the one identifier used in config, in
    #: ``slop check`` and in a ``slop: ignore[...]`` comment.
    name: ClassVar[str]
    #: one line saying what the rule checks, for ``slop rules``.
    description: ClassVar[str]
    #: the altitudes this rule is defined at; the dispatcher visits exactly these.
    altitudes: ClassVar[frozenset[ScopeKind]]

    @classmethod
    @abstractmethod
    def default_config(cls) -> RuleConfig:
        """The rule's shipped settings. Its ``options`` are the only options a config may
        set for it, and their types are the types a config must use."""
        ...

    @abstractmethod
    def check(self, component: Scope, config: RuleConfig) -> Iterable[Violation]:
        """Inspect ONE component, guaranteed to be of a declared altitude, and yield a
        violation for each way it breaks the rule. Must not traverse beyond it."""
        ...
