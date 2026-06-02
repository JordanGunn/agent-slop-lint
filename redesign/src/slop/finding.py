"""Findings — slop's output ontology.

Two **orthogonal** axes (see DESIGN.md "Finding Ontology"):

- **Disposition** (epistemic — what slop claims): ``VERDICT`` (a defect with a
  deterministically prescribable fix) vs ``OBSERVATION`` (a claim-free evidential
  nudge where no remedy can be honestly prescribed).
- **Severity** (operational — what it does to the build): ``ERROR`` (exit 1) >
  ``WARNING`` > ``INFO`` > ``OFF``.

``Verdict`` and ``Observation`` are **distinct types** sharing the ``Finding``
protocol — not one dataclass with a disposition flag and half-inert optional
fields. The disposition-level illegal states are therefore unrepresentable by
construction: an ``Observation`` has no ``prescription`` field to set and its
``severity`` is a pinned ``ClassVar`` (it cannot gate a build — a build failure is
itself a precision claim, and an observation makes none). The intra-verdict
constraints (severity tier, REVIEW cap) are checked in ``__post_init__`` because
they are cross-field on one type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .scope.identity import ScopeId


class Severity(IntEnum):
    """Operational severity. Ordered so members compare directly."""

    OFF = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

    def label(self) -> str:
        return self.name.lower()


class Disposition(StrEnum):
    VERDICT = "verdict"
    OBSERVATION = "observation"


class Action(StrEnum):
    """What a consumer should DO about a finding.

    The deterministic correctives apply to ordinary verdicts. ``REVIEW`` is a
    verdict whose remedy is deferred — slop is confident the structure is
    anomalous but the fix is disjunctive and depends on a judgment slop does not
    make (it does not adjudicate intent). ``INVESTIGATE`` is the terminal action
    of an observation: no prescribed fix, only evidence worth looking at.
    """

    # deterministic correctives
    EXTRACT_CLASS = "extract-class"
    EXTRACT_HELPER = "extract-helper-function"
    EXTRACT_CONSTANT = "extract-shared-constant"
    SPLIT_MODULE = "split-module"
    EXTRACT_SUBPACKAGE = "extract-subpackage"
    FLATTEN_PACKAGE = "flatten-package"
    NARROW_SCOPE = "narrow-scope-or-rename"
    DROP_REDUNDANT_TOKENS = "drop-redundant-tokens"
    RENAME_BY_TEMPLATE = "rename-by-template"
    REPLACE_WITH_DOMAIN_TERM = "replace-with-domain-term"
    REDUCE_COMPLEXITY = "reduce-complexity"
    # intent-deferred verdict (caps at WARNING — see Verdict.__post_init__)
    REVIEW = "review"
    # observation terminal
    INVESTIGATE = "investigate"


# Verdict actions whose remedy is deferred: they may never gate the build.
DEFERRED_ACTIONS: frozenset[Action] = frozenset({Action.REVIEW})


@runtime_checkable
class Finding(Protocol):
    """The common surface of every finding, for the output pipeline."""

    rule: str
    component: ScopeId
    message: str

    @property
    def disposition(self) -> Disposition: ...
    @property
    def severity(self) -> Severity: ...
    def as_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Evidence:
    """The empirical payload an observation carries instead of a defect claim.

    ``kind`` names the measurement (e.g. ``"token-distribution"``); ``data`` is
    the JSON-serialisable evidence. The observation's ``message`` is the
    natural-language transform of this data — the form an agent investigates.
    """

    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "data": self.data}


@dataclass(frozen=True)
class Verdict:
    """A defect: the action is agreed and the fix is prescribable.

    Invariants (enforced at construction): severity is WARNING or ERROR; the
    action is corrective or REVIEW (never INVESTIGATE); a prescription is present;
    a REVIEW verdict caps at WARNING (it cannot gate the build).
    """

    rule: str
    component: ScopeId
    action: Action
    prescription: str
    severity: Severity = Severity.WARNING
    message: str = ""
    value: float | int | None = None
    threshold: float | int | None = None
    confidence: float = 1.0
    line: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    disposition: ClassVar[Disposition] = Disposition.VERDICT

    def __post_init__(self) -> None:
        if self.action is Action.INVESTIGATE:
            raise ValueError("INVESTIGATE is the observation action; a verdict carries a corrective or REVIEW action")
        if self.severity not in (Severity.WARNING, Severity.ERROR):
            raise ValueError(f"a verdict's severity must be WARNING or ERROR, got {self.severity.label()}")
        if not self.prescription:
            raise ValueError("a verdict must carry a prescription")
        if self.action in DEFERRED_ACTIONS and self.severity is Severity.ERROR:
            raise ValueError("REVIEW verdicts cap at WARNING; a deferred-remedy finding cannot gate the build")

    def as_dict(self) -> dict[str, Any]:
        return {
            "disposition": self.disposition.value,
            "rule": self.rule,
            "component": self.component.qualname,
            "kind": self.component.kind.value,
            "severity": self.severity.label(),
            "action": self.action.value,
            "prescription": self.prescription,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "confidence": self.confidence,
            "line": self.line,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class Observation:
    """A claim-free empirical nudge. Severity and action are pinned ClassVars —
    an observation can neither carry a prescription (no such field) nor gate the
    build (severity is INFO, immutable)."""

    rule: str
    component: ScopeId
    evidence: Evidence
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    disposition: ClassVar[Disposition] = Disposition.OBSERVATION
    action: ClassVar[Action] = Action.INVESTIGATE
    severity: ClassVar[Severity] = Severity.INFO

    def __post_init__(self) -> None:
        if not self.message:
            raise ValueError("an observation must carry a natural-language message narrating its evidence")

    def as_dict(self) -> dict[str, Any]:
        return {
            "disposition": self.disposition.value,
            "rule": self.rule,
            "component": self.component.qualname,
            "kind": self.component.kind.value,
            "severity": self.severity.label(),
            "action": self.action.value,
            "message": self.message,
            "evidence": self.evidence.as_dict(),
            "metadata": self.metadata,
        }
