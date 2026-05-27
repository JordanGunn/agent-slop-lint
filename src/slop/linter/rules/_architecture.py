"""Shared zone-rule dispatch for ``rigidity`` / ``uselessness``.

Both Martin 1994 D' rules follow the same shape: filter packages to
one zone (``pain`` or ``uselessness``), check D' against the per-zone
threshold, emit a Slop per offender. ``_run_zone_rule`` parameterises
the zone and threshold; ``_slop_for`` builds the package-scope finding.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.config import Config
from slop.linter.rule import Rule
from slop.linter.slop import Slop
from slop.linter.types import RuleResult

if TYPE_CHECKING:
    from slop.structure.view import Structure


def _slop_for(
    pkg, rule_name: str, threshold: float, severity: str, zone_label: str,
) -> Slop:
    """Build a package-scope Slop finding for a zone violation."""
    return Slop(
        rule=rule_name,
        file=pkg.name,
        line=None,
        symbol=None,
        message=(
            f"Zone of {zone_label} — D'={pkg.distance:.2f} exceeds {threshold} "
            f"(I={pkg.instability or 0:.2f}, A={pkg.abstractness or 0:.2f})"
        ),
        severity=severity,
        value=pkg.distance,
        threshold=threshold,
        metadata={
            "zone": pkg.zone,
            "instability": pkg.instability,
            "abstractness": pkg.abstractness,
            "ca": pkg.ca,
            "ce": pkg.ce,
            "na": pkg.na,
            "nc": pkg.nc,
            "language": pkg.language,
        },
        scope="package",
    )


def _run_zone_rule(
    structure: Structure,
    rule_config: Rule,
    slop_config: Config,
    *,
    rule_name: str,
    zone: str,
    zone_label: str,
    default_threshold: float,
) -> RuleResult:
    """Filter packages to one zone and threshold-check D' (package scope)."""
    thresholds = rule_config.params.get("thresholds", {}) or {}
    if "package" not in thresholds:
        return RuleResult(
            rule=rule_name, status="pass", violations=[],
            summary={"packages_analyzed": 0, "languages_filter": None,
                     "violation_count": 0},
        )
    threshold = float(thresholds.get("package", default_threshold))
    severity = rule_config.severity

    root = slop_config.root or "."
    languages_filter = (
        rule_config.params.get("languages") or slop_config.languages or None
    )

    if languages_filter:
        all_packages: list = []
        for lang in languages_filter:
            sliced = structure.where(language=lang)
            all_packages.extend(sliced.packages(root))
        packages = all_packages
    else:
        packages = structure.packages(root)

    violations: list[Slop] = []
    for pkg in packages:
        if pkg.zone != zone:
            continue
        if pkg.distance is None or pkg.distance <= threshold:
            continue
        violations.append(_slop_for(pkg, rule_name, threshold, severity, zone_label))

    return RuleResult(
        rule=rule_name,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "packages_analyzed": len(packages),
            "languages_filter": list(languages_filter) if languages_filter else None,
            "violation_count": len(violations),
        },
    )
