"""Output formatters for slop.

Three public surfaces, dotref-accessed:

- ``format.human(result)`` — human-readable terminal output (default)
- ``format.quiet(result)`` — one-line summary
- ``format.as_dict(result)`` — JSON-serialisable dict (CLI ``--output json``)

The bulk of human-render machinery lives in ``format.render``. This
module is the public entry point.
"""
from __future__ import annotations

from slop.linter.format.render import (
    DEFAULT_MAX_VIOLATIONS,
    _format_footer,
    human,
)
from slop.linter.result import Result


__all__ = ["DEFAULT_MAX_VIOLATIONS", "human", "quiet", "as_dict"]


def quiet(result: Result) -> str:
    """One-line summary output."""
    return _format_footer(result)


def as_dict(result: Result) -> dict:
    """Format a Result as a JSON-serialisable dict.

    Returned by ``Result.json()``. The CLI's ``--output json`` mode
    serialises with ``json.dumps()`` at the output boundary.
    """
    out: dict = {
        "version": result.version,
        "root": result.root,
        "languages": result.languages,
        "rules": {},
        "summary": {
            "rules_checked": result.rules_checked,
            "rules_skipped": result.rules_skipped,
            "violation_count": result.slop_count,
            "advisory_count": result.advisory_count,
            "observation_count": result.observation_count,
            "result": result.verdict,
        },
    }

    for rule_name, rr in result.rule_results.items():
        violations_out = []
        for v in rr.violations:
            violations_out.append({
                "rule": v.rule,
                "scope": v.scope,
                "file": v.file,
                "line": v.line,
                "symbol": v.symbol,
                "message": v.message,
                "severity": v.severity,
                "value": v.value,
                "threshold": v.threshold,
                "action": str(v.action) if v.action else None,
                "prescription": v.prescription,
                "confidence": v.confidence,
                "metadata": v.metadata,
            })
        observations_out = []
        for v in rr.observations:
            observations_out.append({
                "rule": v.rule,
                "scope": v.scope,
                "file": v.file,
                "line": v.line,
                "symbol": v.symbol,
                "message": v.message,
                "severity": v.severity,
                "disposition": str(v.disposition),
                "action": str(v.action) if v.action else None,
                "evidence": v.evidence.as_dict() if v.evidence else None,
                "metadata": v.metadata,
            })
        out["rules"][rule_name] = {
            "status": rr.status,
            "violations": violations_out,
            "observations": observations_out,
            "summary": rr.summary,
            "errors": rr.errors,
        }

    return out
