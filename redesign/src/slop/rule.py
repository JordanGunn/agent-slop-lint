"""Rule contract.

A rule **declares** the altitude(s) it is defined at (``altitudes``); the
dispatcher (``slop.dispatch``) walks the component tree and invokes the rule at
every component of that altitude. A rule **never walks the corpus itself** — it
inspects the single component it is handed. This is what makes the
"enabled-but-checks-nothing" bug class unrepresentable: a rule cannot run where it
is undefined, and the dispatcher asserts it visited >0 components.

A rule is *only* a threshold check + finding emission over a metric. It does not
re-derive a metric — every measurement lives on a metric view constructed over the
component (``Structure.over(component)`` for structural signals,
``Lexical.over(component)`` for lexical ones, or ``component.lexicon()`` for the raw
token space). The scope entities themselves are metric-free (the scope/metrics
sever); ``slop.model`` no longer exists.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import ClassVar

from .scope.base import Scope
from .scope.identity import ScopeKind
from .config import RuleConfig
from .finding import Finding


class Rule(ABC):
    #: dotted rule name (e.g. ``"complexity.cyclomatic"``).
    name: ClassVar[str]
    #: the altitudes this rule is defined at; the dispatcher visits exactly these.
    altitudes: ClassVar[frozenset[ScopeKind]]

    @classmethod
    @abstractmethod
    def default_config(cls) -> RuleConfig:
        """The rule's shipped defaults. Threshold keys MUST be a subset of
        ``altitudes`` (config validation enforces this at load)."""
        ...

    @abstractmethod
    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        """Inspect ONE component — guaranteed to be of a declared altitude — and
        yield findings. Must not traverse beyond the given component."""
        ...
