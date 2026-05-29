"""``Result`` — the user-facing report from ``Linter.run()``.

One run, one Result, one verdict. ``json()`` returns a dict;
``pretty()`` returns a string. Both delegate to ``slop.linter.format``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .types import RuleResult


@dataclass
class Result:
    """The user-facing report from one ``Linter.run()``."""

    version: str
    root: str
    languages: list[str]
    display_root: str = ""
    rule_results: dict[str, RuleResult] = field(default_factory=dict)
    rules_checked: int = 0
    rules_skipped: int = 0
    slop_count: int = 0
    advisory_count: int = 0
    observation_count: int = 0
    waived_count: int = 0
    verdict: str = "pass"

    def json(self) -> dict[str, Any]:
        """Canonical machine-readable representation (dict).

        The CLI's ``--output json`` mode serialises this with
        ``json.dumps()`` at the output boundary.
        """
        from slop.linter import format
        return format.as_dict(self)

    def pretty(self, *, verbose: bool = True, max_violations: int | None = None) -> str:
        """Human-readable terminal output.

        ``verbose=True`` returns the full per-category block.
        ``verbose=False`` returns the one-line summary.
        """
        from slop.linter import format
        if not verbose:
            return format.quiet(self)
        cap = max_violations if max_violations is not None else format.DEFAULT_MAX_VIOLATIONS
        return format.human(self, max_violations=cap)
