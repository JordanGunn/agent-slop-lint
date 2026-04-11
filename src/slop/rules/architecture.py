"""Architecture rules — wraps aux robert_kernel.

Rules:
  packages  — fail if any package's D' exceeds threshold or lands in a forbidden zone
"""

from __future__ import annotations

from pathlib import Path

from aux.kernels.robert import robert_kernel

from slop.models import RuleConfig, RuleResult, SlopConfig, Violation

# robert_kernel only supports go and python
_SUPPORTED_LANGUAGES = {"go", "python"}


def run_distance(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig
) -> RuleResult:
    """Check Robert C. Martin Distance from the Main Sequence."""
    max_distance = rule_config.params.get("max_distance", 0.7)
    fail_on_zone = set(rule_config.params.get("fail_on_zone", ["pain"]))
    severity = rule_config.severity

    # Determine which languages to analyze
    rule_languages = rule_config.params.get("languages", [])
    if rule_languages:
        languages = [lang for lang in rule_languages if lang in _SUPPORTED_LANGUAGES]
    elif slop_config.languages:
        languages = [lang for lang in slop_config.languages if lang in _SUPPORTED_LANGUAGES]
    else:
        languages = list(_SUPPORTED_LANGUAGES)

    if not languages:
        return RuleResult(
            rule="packages",
            status="skip",
            summary={"reason": "no supported languages (robert requires go or python)"},
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
            triggered = False
            reasons: list[str] = []

            if pkg.distance is not None and pkg.distance > max_distance:
                triggered = True
                reasons.append(f"D'={pkg.distance:.2f} exceeds {max_distance}")

            if pkg.zone in fail_on_zone:
                triggered = True
                reasons.append(f"Zone of {pkg.zone.title()}")

            if triggered:
                violations.append(
                    Violation(
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
                )

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
