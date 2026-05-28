"""``Slop`` — the v2.0 finding type.

Carries the structured corrective-action layer agents consume. Each
finding emits a bounded ``action`` (enum-like label), a concrete
``prescription`` (specific instruction for THIS finding), and a
``confidence`` aggregating the battery signals.

Output-side type — semantically distinct from the parse-entity records
in ``corpus/records.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Action(StrEnum):
    """Bounded vocabulary of corrective actions a rule can prescribe.

    Each rule's diagnostic maps to exactly one. The action determines
    what an agent reading slop's output should DO; the per-finding
    ``prescription`` field describes how to do it for the specific case.
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
    REPLACE_WITH_SYMBOL = "replace-with-symbol"
    REDUCE_COMPLEXITY = "reduce-complexity"
    REVIEW_INTENT = "review-intent"
    ACCEPT_AS_FRAMEWORK = "accept-as-framework"
    NOTE_PATTERN = "note-pattern"


@dataclass
class Slop:
    """A finding emitted by a rule.

    The ``scope`` field declares the emission unit (``function``, ``class``,
    ``module``, ``parameter``, ``package``) — first-class since the
    scope-as-first-class refactor. ``None`` is reserved for cross-cutting
    rules whose emission unit doesn't map to a single scope (cycles, hotspot
    files, orphan symbols).

    The corrective-action triple (``action``, ``prescription``,
    ``confidence``) is the structured layer agents consume. ``message``
    remains the human-readable prose; the triple is the machine-actionable
    instruction.
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
