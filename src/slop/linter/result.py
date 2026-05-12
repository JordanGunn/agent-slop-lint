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
    waived_count: int = 0
    verdict: str = "pass"

    def json(self) -> dict[str, Any]:
        """Canonical machine-readable representation (dict).

        The CLI's ``--output json`` mode serialises this with
        ``json.dumps()`` at the output boundary.
        """
        from .format import to_dict
        return to_dict(self)

    def pretty(self, *, verbose: bool = True, max_violations: int | None = None) -> str:
        """Human-readable terminal output.

        ``verbose=True`` returns the full per-category block.
        ``verbose=False`` returns the one-line summary.
        """
        from .format import DEFAULT_MAX_VIOLATIONS, format_human, format_quiet
        if not verbose:
            return format_quiet(self)
        cap = max_violations if max_violations is not None else DEFAULT_MAX_VIOLATIONS
        return format_human(self, max_violations=cap)
