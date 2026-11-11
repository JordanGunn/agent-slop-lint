"""Dispatcher: runs each enabled rule at the components it is defined at.

The dispatcher owns traversal. It walks the component tree once, indexes components by
altitude, and calls each enabled rule at every component of its *declared* altitudes;
rules never walk the corpus themselves. Two things follow:

- A rule runs only where it declares itself defined, so a misconfigured rule cannot
  silently check nothing.
- A rule that examined zero components (its altitude is absent, or everything was
  excluded) is reported in ``zero_visited`` instead of passing as clean.

A violation on a line carrying ``slop: ignore`` is dropped, and ``slop: ignore[a, b]``
drops only the rules named, like a ``noqa`` comment: the exemption sits beside the code
it excuses, in whatever comment syntax the language has.

A rule marked ``subjective`` yields warnings, kept apart from violations and never failing
the run.

Exit codes: 0 no violations (warnings allowed), 1 at least one violation, 2 slop could not
run (raised by the CLI).
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .config import AnalysisConfig
from .rule import Rule
from .scope.identity import ScopeKind
from .violation import Violation

_SUPPRESSION = re.compile(r"slop:\s*ignore(?:\[([^\]]*)\])?")


@dataclass
class Report:
    #: objective violations: the only findings that fail the run
    violations: list[Violation]
    #: subjective violations (WARN): reported, never fail the run
    warnings: list[Violation] = field(default_factory=list)
    visited: dict[str, int] = field(default_factory=dict)
    zero_visited: list[str] = field(default_factory=list)
    root: str | None = None

    def exit_code(self) -> int:
        return 1 if self.violations else 0

    def relative_path(self, violation: Violation) -> str | None:
        """The violation's path relative to the scan root, so a report does not leak an
        absolute machine path."""
        if violation.path and self.root:
            try:
                return os.path.relpath(violation.path, self.root)
            except ValueError:
                pass
        return violation.path

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": {"violations": len(self.violations), "warnings": len(self.warnings),
                        "exit_code": self.exit_code()},
            "violations": [{**v.as_dict(), "path": self.relative_path(v)} for v in self.violations],
            "warnings": [{**v.as_dict(), "path": self.relative_path(v)} for v in self.warnings],
            "zero_visited": self.zero_visited,
        }


class Dispatcher:
    def __init__(self, rules: Iterable[Rule], config: AnalysisConfig) -> None:
        self._rules = list(rules)
        self._config = config

    def run(self, corpus: Any) -> Report:
        by_kind = _index_by_kind(corpus)
        found: list[Violation] = []
        warned: list[Violation] = []
        visited: dict[str, int] = {}
        zero_visited: list[str] = []

        for rule in self._rules:
            rc = self._config.for_rule(rule.name)
            if rc is None or not rc.enabled:
                continue
            count = 0
            for kind in rule.altitudes:
                for component in by_kind.get(kind, ()):
                    count += 1
                    (warned if rule.subjective else found).extend(rule.check(component, rc))
            visited[rule.name] = count
            if count == 0:
                zero_visited.append(rule.name)

        lines = _Lines()
        kept = [v for v in found if not lines.suppresses(v)]
        kept.sort(key=lambda v: (v.path or "", v.line, v.column, v.rule))
        kept_warnings = [v for v in warned if not lines.suppresses(v)]
        kept_warnings.sort(key=lambda v: (v.path or "", v.line, v.column, v.rule))
        return Report(violations=kept, warnings=kept_warnings, visited=visited, zero_visited=zero_visited,
                      root=str(corpus.root) if hasattr(corpus, "root") else None)


class _Lines:
    """The source lines of each file a violation points into, read once."""

    def __init__(self) -> None:
        self._files: dict[str, list[str]] = {}

    def suppresses(self, violation: Violation) -> bool:
        if not violation.path:
            return False
        if violation.path not in self._files:
            try:
                with open(violation.path, encoding="utf-8", errors="replace") as f:
                    self._files[violation.path] = f.read().splitlines()
            except OSError:
                self._files[violation.path] = []
        lines = self._files[violation.path]
        if not 1 <= violation.line <= len(lines):
            return False
        match = _SUPPRESSION.search(lines[violation.line - 1])
        if match is None:
            return False
        if match.group(1) is None:
            return True
        named = {name.strip() for name in match.group(1).split(",") if name.strip()}
        return violation.rule in named


def _index_by_kind(root: Any) -> dict[ScopeKind, list[Any]]:
    out: dict[ScopeKind, list[Any]] = {k: [] for k in ScopeKind}
    stack = [root]
    while stack:
        component = stack.pop()
        out[component.id.kind].append(component)
        stack.extend(component.children())
    return out
