"""Architecture rules — wraps the vendored robert_kernel.

Rules:
  packages  — fail if any package's D' exceeds threshold or lands in a forbidden zone
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.robert import robert_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation

# Languages robert_kernel can compute Distance from the Main Sequence for.
# Must stay in sync with _LANG_GLOBS in slop._structural.robert.
_SUPPORTED_LANGUAGES = {
    "go",
    "python",
    "java",
    "c_sharp",
    "typescript",
    "javascript",
    "rust",
}


def _resolve_languages(rule_languages, slop_languages):
    """Narrow a language selection to what robert_kernel supports."""
    candidates = rule_languages or slop_languages or _SUPPORTED_LANGUAGES
    return [lang for lang in candidates if lang in _SUPPORTED_LANGUAGES]


def _check_package(pkg, max_distance, fail_on_zone, severity):
    """Return a Violation if the package breaches distance or zone limits."""
    reasons: list[str] = []
    if pkg.distance is not None and pkg.distance > max_distance:
        reasons.append(f"D'={pkg.distance:.2f} exceeds {max_distance}")
    if pkg.zone in fail_on_zone:
        reasons.append(f"Zone of {pkg.zone.title()}")
    if not reasons:
        return None
    return Violation(
        rule="packages",
        file=pkg.package,
        line=None,
        symbol=None,
        message="; ".join(reasons)
        + f" (I={pkg.instability or 0:.2f}, A={pkg.abstractness or 0:.2f})",
        severity=severity,
        value=pkg.distance,
        threshold=max_distance,
        metadata={
            "zone": pkg.zone,
            "instability": pkg.instability,
            "abstractness": pkg.abstractness,
            "ca": pkg.ca,
            "ce": pkg.ce,
            "language": pkg.language,
        },
    )


def run_distance(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Check Robert C. Martin Distance from the Main Sequence."""
    max_distance = rule_config.params.get("max_distance", 0.7)
    fail_on_zone = set(rule_config.params.get("fail_on_zone", ["pain"]))
    severity = rule_config.severity

    languages = _resolve_languages(
        rule_config.params.get("languages", []),
        slop_config.languages or [],
    )

    if not languages:
        return RuleResult(
            rule="packages",
            status="skip",
            summary={
                "reason": "no supported languages",
                "supported": sorted(_SUPPORTED_LANGUAGES),
            },
        )

    violations: list[Violation] = []
    all_errors: list[str] = []
    packages_analyzed = 0

    for lang in languages:
        result = robert_kernel(
            root=root,
            language=lang,
            excludes=slop_config.exclude or None,
        )
        all_errors.extend(result.errors)
        packages_analyzed += result.packages_analyzed
        for pkg in result.packages:
            v = _check_package(pkg, max_distance, fail_on_zone, severity)
            if v is not None:
                violations.append(v)

    return RuleResult(
        rule="packages",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "packages_analyzed": packages_analyzed,
            "languages": languages,
            "violation_count": len(violations),
        },
        errors=all_errors,
    )
