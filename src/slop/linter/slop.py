"""``Slop`` — the v2.0 finding type.

Carries the structured layer agents consume. A finding has a
``disposition``: a VERDICT (a defect, with a bounded ``action`` + a
concrete ``prescription`` + a ``confidence``) or an OBSERVATION (a
claim-free empirical nudge, carrying ``evidence`` instead of a defect
claim). The two share one type because they ride the same output
pipeline; the disposition tells a consumer which kind it is.

Output-side type — semantically distinct from the parse-entity records
in ``corpus/records.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Action(StrEnum):
    """Bounded vocabulary of actions a finding can carry.

    For a VERDICT the action is corrective — it determines what an agent
    reading slop's output should DO, with the per-finding ``prescription``
    describing how for the specific case. ``INVESTIGATE`` is the terminal
    action for an OBSERVATION: there is no prescribed fix, only evidence
    worth looking at.
    """

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
    REVIEW_INTENT = "review-intent"
    ACCEPT_AS_FRAMEWORK = "accept-as-framework"
    NOTE_PATTERN = "note-pattern"
    INVESTIGATE = "investigate"


class Disposition(StrEnum):
    """Whether a finding asserts a defect or merely reports evidence.

    ``VERDICT`` — a threshold-gated defect; the corrective triple
    (``action`` + ``prescription`` + ``confidence``) applies and the
    finding counts toward the run's violation/advisory tally.

    ``OBSERVATION`` — a claim-free empirical nudge; it carries
    ``evidence`` (and a natural-language ``message`` narrating it),
    asserts no defect, and never affects the verdict. The agent supplies
    the judgment slop deliberately withholds. Used where a measurement is
    informative but no remedy can be honestly prescribed.
    """

    VERDICT = "verdict"
    OBSERVATION = "observation"


@dataclass(frozen=True)
class Evidence:
    """Structured empirical payload carried by an OBSERVATION finding.

    ``kind`` names the measurement (e.g. ``"token-distribution"``).
    ``data`` is the JSON-serialisable evidence object. The finding's
    ``message`` holds the natural-language transform of this data — the
    form an agent actually investigates. ``Evidence`` keeps the raw
    numbers alongside that prose so a machine consumer can act on either.
    """

    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "data": self.data}


@dataclass
class Slop:
    """A finding emitted by a rule.

    The ``scope`` field declares the emission unit (``function``, ``class``,
    ``module``, ``parameter``, ``package``) — first-class since the
    scope-as-first-class refactor. ``None`` is reserved for cross-cutting
    rules whose emission unit doesn't map to a single scope (cycles, hotspot
    files, orphan symbols).

    ``disposition`` selects the finding's kind. For a VERDICT the
    corrective triple (``action``, ``prescription``, ``confidence``) is the
    machine-actionable instruction and ``message`` is its prose. For an
    OBSERVATION, ``evidence`` carries the empirical object and ``message``
    is its natural-language narration; the corrective triple is inert
    (``action`` is ``INVESTIGATE``, no prescription).
    """

    rule: str
    file: str
    line: int | None = None
    symbol: str | None = None
    message: str = ""
    severity: str = "error"
    value: float | int | None = None
    threshold: float | int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    suggestion: str | None = None
    scope: str | None = None
    action: Action | None = None
    prescription: str | None = None
    confidence: float = 0.0
    disposition: Disposition = Disposition.VERDICT
    evidence: Evidence | None = None
