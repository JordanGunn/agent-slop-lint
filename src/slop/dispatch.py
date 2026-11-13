"""Dispatcher: runs each enabled rule at the scopes it is defined at.

The dispatcher owns traversal. It walks the scope tree once, indexes scopes by
altitude, and calls each enabled rule at every scope of its *declared* altitudes;
rules never walk the corpus themselves. Two things follow:

- A rule runs only where it declares itself defined, so a misconfigured rule cannot
  silently check nothing.
- A rule that examined zero scopes (its altitude is absent, or everything was
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
from pathlib import Path
from operator import attrgetter
from typing import Any

from .config import AnalysisConfig, RuleConfig
from .rule import Rule
from .scope.find import walk
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
        return self.relative(violation.path)

    def relative(self, path: str | None) -> str | None:
        """``path`` relative to the scan root, or as given when there is none."""
        if path and self.root:
            try:
                return os.path.relpath(path, self.root)
            except ValueError:
                pass
        return path

    def _entry(self, violation: Violation) -> dict[str, Any]:
        """One finding as JSON, with its path and its scopes' paths relative to the root."""
        entry = violation.as_dict()
        entry["path"] = self.relative_path(violation)
        for scope in (entry["scope"], *entry["related"]):
            if scope is not None:
                scope["path"] = self.relative(scope["path"])
        return entry

    def as_dict(self) -> dict[str, Any]:
        """The report as JSON-ready data. ``root`` is the absolute scan root that each ``path``
        is relative to, so a reader can open a finding from any working directory."""
        return {
            "root": str(Path(self.root).resolve()) if self.root else None,
            "summary": {"violations": len(self.violations), "warnings": len(self.warnings),
                        "exit_code": self.exit_code()},
            "violations": [self._entry(v) for v in self.violations],
            "warnings": [self._entry(v) for v in self.warnings],
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
            config = self._config.for_rule(rule.name)
            if config is None or not config.enabled:
                continue
            count, violations = _run_rule(rule, config, by_kind)
            visited[rule.name] = count
            if count == 0:
                zero_visited.append(rule.name)
            (warned if rule.subjective else found).extend(violations)

        return _report(found, warned, visited, zero_visited, corpus)


def _run_rule(rule: Rule, config: RuleConfig, by_kind: dict[ScopeKind, list[Any]]) -> tuple[int, list[Violation]]:
    """Run ``rule`` at every scope of its declared altitudes; return how many
    scopes it was run at and what it found."""
    violations: list[Violation] = []
    count = 0
    for kind in rule.altitudes:
        for scope in by_kind.get(kind, ()):
            count += 1
            violations.extend(rule.check(scope, config))
    return count, violations


def _report(found: list[Violation], warned: list[Violation], visited: dict[str, int],
            zero_visited: list[str], corpus: Any) -> Report:
    """Assemble the report, dropping the findings a ``slop: ignore`` comment suppresses."""
    lines = _Lines()
    return Report(
        violations=_kept(found, lines), warnings=_kept(warned, lines),
        visited=visited, zero_visited=zero_visited,
        root=str(corpus.root) if hasattr(corpus, "root") else None,
    )


def _kept(violations: list[Violation], lines: "_Lines") -> list[Violation]:
    """The violations no source line suppresses, ordered by position."""
    kept = [violation for violation in violations if not lines.suppresses(violation)]
    kept.sort(key=attrgetter("position"))
    return kept


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
    for scope in walk(root):
        out[scope.id.kind].append(scope)
    return out
