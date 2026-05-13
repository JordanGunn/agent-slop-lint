"""Architecture rules — Robert C. Martin package design metrics, split by failure mode.

Two rules consume ``slop._structural.robert.robert_kernel`` (Distance from
the Main Sequence, D' = |A + I - 1|). Each names one of the two failure
modes off the main sequence so the rule that fires identifies the kind
of problem:

  ``structural.packages.rigidity``     — Zone of Pain (low I, low A):
    stable + concrete packages are rigid under changing requirements.
    Many depend on them, they can't be extended without breaking
    callers.

  ``structural.packages.uselessness``  — Zone of Uselessness (high I,
    high A): unstable + abstract packages are pure indirection with
    no dependents. Abstractions exist but no one calls through them.

D' is the same metric for both; the zone is what distinguishes the
failure. Each rule has its own ``threshold`` for how far off the main
sequence the package must drift before flagging — surfacing rigidity
and uselessness at different sensitivities is the point of the split.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.robert import robert_kernel
from slop.config.models import RuleConfig, SlopConfig
from slop.linter.slop import Slop
from slop.linter.types import RuleResult

# Languages robert_kernel can compute D' for. Must stay in sync with
# _LANG_GLOBS in slop._structural.robert.
_SUPPORTED_LANGUAGES = {
    "go", "python", "java", "c_sharp", "typescript", "javascript", "rust",
}


def _resolve_languages(rule_languages, slop_languages):
    """Narrow a language selection to what robert_kernel supports."""
    candidates = rule_languages or slop_languages or _SUPPORTED_LANGUAGES
    return [lang for lang in candidates if lang in _SUPPORTED_LANGUAGES]


def _run_kernel(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> tuple[list, list[str], int, list[str]]:
    """Run robert_kernel across every resolved language, aggregating results.

    Returns ``(packages, errors, packages_analyzed, languages)``. Packages
    are pooled across languages; the caller filters by zone.
    """
    languages = _resolve_languages(
        rule_config.params.get("languages", []),
        slop_config.languages or [],
    )
    packages: list = []
    errors: list[str] = []
    analyzed = 0
    for lang in languages:
        result = robert_kernel(
            root=root, language=lang, excludes=slop_config.exclude or None,
        )
        errors.extend(result.errors)
        analyzed += result.packages_analyzed
        packages.extend(result.packages)
    return packages, errors, analyzed, languages


def _slop_for(
    pkg, rule_name: str, threshold: float, severity: str, zone_label: str,
) -> Slop:
    return Slop(
        rule=rule_name,
        file=pkg.package,
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
            "language": pkg.language,
        },
    )


def _run_zone_rule(
    root: Path,
    rule_config: RuleConfig,
    slop_config: SlopConfig,
    *,
    rule_name: str,
    zone: str,
    zone_label: str,
    default_threshold: float,
) -> RuleResult:
    """Common worker — filter packages to one zone and threshold-check D'."""
    threshold = rule_config.params.get("threshold", default_threshold)
    severity = rule_config.severity

    languages = _resolve_languages(
        rule_config.params.get("languages", []),
        slop_config.languages or [],
    )
    if not languages:
        return RuleResult(
            rule=rule_name,
            status="skip",
            summary={
                "reason": "no supported languages",
                "supported": sorted(_SUPPORTED_LANGUAGES),
            },
        )

    packages, errors, analyzed, _ = _run_kernel(root, rule_config, slop_config)
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
            "packages_analyzed": analyzed,
            "languages": languages,
            "violation_count": len(violations),
        },
        errors=errors,
    )


def run_rigidity(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag Zone-of-Pain packages whose D' exceeds the rigidity threshold.

    Pain: I < 0.3 AND A < 0.3 — stable (many callers) AND concrete
    (no abstractions to substitute through). The package is locked in
    by its callers and lacks extension points.
    """
    return _run_zone_rule(
        root, rule_config, slop_config,
        rule_name="structural.packages.rigidity",
        zone="pain",
        zone_label="Pain",
        default_threshold=0.7,
    )


def run_uselessness(
    root: Path, rule_config: RuleConfig, slop_config: SlopConfig,
) -> RuleResult:
    """Flag Zone-of-Uselessness packages whose D' exceeds the uselessness threshold.

    Uselessness: I > 0.7 AND A > 0.7 — unstable (few or no callers)
    AND abstract (heavy on interfaces). Abstractions exist but nothing
    uses them; the indirection is wasted.
    """
    return _run_zone_rule(
        root, rule_config, slop_config,
        rule_name="structural.packages.uselessness",
        zone="uselessness",
        zone_label="Uselessness",
        default_threshold=0.7,
    )
