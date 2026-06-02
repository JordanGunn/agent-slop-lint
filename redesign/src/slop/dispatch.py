"""Dispatcher — altitude-driven rule execution.

The dispatcher owns traversal: it walks the component tree once, indexes
components by altitude, and invokes each enabled rule at every component of its
*declared* altitudes. Rules never walk the corpus themselves.

Two invariants fall out of this:

- A rule runs only where it declares itself defined — the legacy "config keyed
  wrong, rule silently checks nothing" failure cannot recur.
- Every enabled rule's visited-count is recorded; a rule that examined zero
  components (its altitude is absent, or all filtered) is surfaced as a
  ``zero_visited`` diagnostic rather than passing silently as "clean".

Exit codes: 0 clean / 1 violations (any ERROR-severity finding) / 2 error
(raised by the CLI, not here). WARNING verdicts and INFO observations are
advisory — they never gate the build.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .scope.identity import ComponentKind
from .config import AnalysisConfig
from .finding import Disposition, Finding, Severity
from .rule import Rule


@dataclass
class Report:
    findings: list[Finding]
    visited: dict[str, int] = field(default_factory=dict)
    zero_visited: list[str] = field(default_factory=list)

    def verdicts(self) -> list[Finding]:
        return [f for f in self.findings if f.disposition is Disposition.VERDICT]

    def observations(self) -> list[Finding]:
        return [f for f in self.findings if f.disposition is Disposition.OBSERVATION]

    def exit_code(self) -> int:
        return 1 if any(f.severity is Severity.ERROR for f in self.findings) else 0

    def as_dict(self) -> dict[str, Any]:
        verdicts = self.verdicts()
        return {
            "summary": {
                "verdicts": len(verdicts),
                "observations": len(self.observations()),
                "errors": sum(1 for f in self.findings if f.severity is Severity.ERROR),
                "warnings": sum(1 for f in self.findings if f.severity is Severity.WARNING),
                "exit_code": self.exit_code(),
            },
            "findings": [f.as_dict() for f in self.findings],
            "zero_visited": self.zero_visited,
        }


class Dispatcher:
    def __init__(self, rules: Iterable[Rule], config: AnalysisConfig) -> None:
        self._rules = list(rules)
        self._config = config

    def run(self, corpus: Any) -> Report:
        by_kind = _index_by_kind(corpus)
        findings: list[Finding] = []
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
                    findings.extend(rule.check(component, rc))
            visited[rule.name] = count
            if count == 0:
                zero_visited.append(rule.name)

        return Report(findings=findings, visited=visited, zero_visited=zero_visited)


def _index_by_kind(root: Any) -> dict[ComponentKind, list[Any]]:
    out: dict[ComponentKind, list[Any]] = {k: [] for k in ComponentKind}
    stack = [root]
    while stack:
        component = stack.pop()
        out[component.id.kind].append(component)
        stack.extend(component.children())
    return out
