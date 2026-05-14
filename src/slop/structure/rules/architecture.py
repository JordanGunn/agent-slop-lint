"""Architecture rules — Robert C. Martin package design metrics, split by failure mode.

Two rules consume ``Structure.packages`` (Martin 1994 Distance from the
Main Sequence, D' = |A + I - 1|). Each names one of the two failure
modes off the main sequence so the rule that fires identifies the kind
of problem:

  ``structural.packages.rigidity``     — Zone of Pain (low I, low A):
    stable + concrete packages are rigid under changing requirements.
    Many packages depend on them, but they have no abstractions to
    substitute through. Changes ripple to every caller.

  ``structural.packages.uselessness``  — Zone of Uselessness (high I,
    high A): unstable + abstract packages are pure indirection with
    no dependents. Abstractions exist but nothing calls through them.

D' is the same metric for both; the zone is what distinguishes the
failure. Each rule has its own ``threshold`` for how far off the main
sequence the package must drift before flagging — surfacing rigidity
and uselessness at different sensitivities is the point of the split.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult

if TYPE_CHECKING:
    from slop.structure.view import Structure


def _slop_for(
    pkg, rule_name: str, threshold: float, severity: str, zone_label: str,
) -> Slop:
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
    )


def _run_zone_rule(
    structure: Structure,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
    *,
    rule_name: str,
    zone: str,
    zone_label: str,
    default_threshold: float,
) -> RuleResult:
    """Filter packages to one zone and threshold-check D'."""
    threshold = rule_config.params.get("threshold", default_threshold)
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


def run_rigidity(
    structure: Structure, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag Zone-of-Pain packages whose D' exceeds the rigidity threshold.

    Pain: I < 0.3 AND A < 0.3 — stable (many callers) AND concrete
    (no abstractions to substitute through). The package is locked in
    by its callers and lacks extension points.
    """
    return _run_zone_rule(
        structure, rule_config, slop_config,
        rule_name="structural.packages.rigidity",
        zone="pain",
        zone_label="Pain",
        default_threshold=0.7,
    )


def run_uselessness(
    structure: Structure, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag Zone-of-Uselessness packages whose D' exceeds the uselessness threshold.

    Uselessness: I > 0.7 AND A > 0.7 — unstable (few or no callers)
    AND abstract (heavy on interfaces). Abstractions exist but nothing
    uses them; the indirection is wasted.
    """
    return _run_zone_rule(
        structure, rule_config, slop_config,
        rule_name="structural.packages.uselessness",
        zone="uselessness",
        zone_label="Uselessness",
        default_threshold=0.7,
    )
