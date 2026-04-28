"""Rule execution engine for slop.

Iterates enabled rules, calls their run functions, collects results,
and computes the aggregate lint result with exit code.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from fnmatch import fnmatchcase
from pathlib import Path

from slop import __version__
from slop.models import LintResult, RuleResult, SlopConfig, Violation, WaiverConfig
from slop.rules import RULE_REGISTRY, RULES_BY_CATEGORY, RULES_BY_NAME


def _select_rules(filter_rule, filter_category):
    """Resolve filters to a list of rules to run.

    Raises KeyError(filter) if the filter matches no rule or category.
    """
    if filter_rule:
        rule_def = RULES_BY_NAME.get(filter_rule)
        if rule_def is not None:
            return [rule_def]
        prefix = filter_rule + "."
        prefix_matches = [r for r in RULE_REGISTRY if r.name.startswith(prefix)]
        if prefix_matches:
            return prefix_matches
        raise KeyError(filter_rule)
    if filter_category:
        matches = RULES_BY_CATEGORY.get(filter_category, [])
        if not matches:
            raise KeyError(filter_category)
        return matches
    return list(RULE_REGISTRY)


def _execute_rule(rule_def, root: Path, rc, config: SlopConfig) -> RuleResult:
    """Run one rule, coercing errors-with-pass to error status.

    A rule that produced errors but no violations should be reported as an
    error, not a pass — otherwise silent failures (e.g. missing binaries,
    unreadable files) render as clean.
    """
    try:
        result = rule_def.run(root, rc, config)
    except Exception as e:
        return RuleResult(
            rule=rule_def.name,
            status="error",
            errors=[f"{type(e).__name__}: {e}"],
        )
    if result.errors and result.status == "pass":
        result.status = "error"
    return result


def run_lint(
    config: SlopConfig,
    *,
    filter_category: str | None = None,
    filter_rule: str | None = None,
    display_root: str = "",
) -> LintResult:
    """Run enabled rules against the configured root.

    Args:
        config: Merged slop configuration.
        filter_category: If set, run only rules in this category.
        filter_rule: If set, run only this specific rule (e.g. "complexity.cyclomatic").

    Returns:
        Aggregated LintResult with per-rule results and summary.
    """
    root = Path(config.root).expanduser().resolve()

    try:
        rules_to_run = _select_rules(filter_rule, filter_category)
    except KeyError as e:
        key = e.args[0]
        label = "rule" if filter_rule else "category"
        return LintResult(
            version=__version__,
            root=str(root),
            languages=config.languages,
            result="error",
            rule_results={
                key: RuleResult(
                    rule=key,
                    status="error",
                    errors=[f"Unknown {label}: {key}"],
                )
            },
        )

    rule_results: dict[str, RuleResult] = {}
    rules_checked = 0
    rules_skipped = 0
    total_violations = 0
    total_advisories = 0
    total_waived = 0

    for rule_def in rules_to_run:
        rc = config.rule_config(rule_def.category)
        if not rc.enabled or rc.severity == "off":
            rule_results[rule_def.name] = RuleResult(rule=rule_def.name, status="skip")
            rules_skipped += 1
            continue

        result = _execute_rule(rule_def, root, rc, config)
        result = _apply_waivers(result, config.waivers, root)
        rule_results[rule_def.name] = result
        rules_checked += 1

        for v in result.violations:
            if v.severity == "error":
                total_violations += 1
            else:
                total_advisories += 1
        total_waived += len(result.waived_violations)

    return LintResult(
        version=__version__,
        root=str(root),
        languages=config.languages,
        display_root=display_root or config.root,
        rule_results=rule_results,
        rules_checked=rules_checked,
        rules_skipped=rules_skipped,
        violation_count=total_violations,
        advisory_count=total_advisories,
        waived_count=total_waived,
        result=_overall_status(rule_results, total_violations),
    )


def _overall_status(rule_results, total_violations) -> str:
    """Collapse per-rule results into a single error/fail/pass verdict."""
    if any(r.status == "error" for r in rule_results.values()):
        return "error"
    if total_violations > 0:
        return "fail"
    return "pass"


def _apply_waivers(
    result: RuleResult,
    waivers: list[WaiverConfig],
    root: Path,
) -> RuleResult:
    """Move matching violations into waived_violations without hiding them."""
    if not waivers or not result.violations:
        return result

    remaining: list[Violation] = []
    waived: list[Violation] = [*result.waived_violations]
    today = date.today()

    for violation in result.violations:
        waiver = _matching_waiver(violation, waivers, root, today)
        if waiver is None:
            remaining.append(violation)
        else:
            waived.append(_mark_waived(violation, waiver))

    result.violations = remaining
    result.waived_violations = waived
    if result.status == "fail" and not remaining:
        result.status = "pass"
    result.summary["waived_count"] = len(waived)
    result.summary["violation_count"] = len(remaining)
    return result


def _matching_waiver(
    violation: Violation,
    waivers: list[WaiverConfig],
    root: Path,
    today: date,
) -> WaiverConfig | None:
    """Find the first active waiver that applies to a violation."""
    for waiver in waivers:
        if _waiver_expired(waiver, today):
            continue
        if not _rule_matches(violation.rule, waiver.rule):
            continue
        if not _path_matches(violation.file, waiver.path, root):
            continue
        if not _value_allowed(violation, waiver):
            continue
        return waiver
    return None


def _waiver_expired(waiver: WaiverConfig, today: date) -> bool:
    """Return whether a waiver's optional expiry date has passed."""
    return waiver.expires is not None and date.fromisoformat(waiver.expires) < today


def _rule_matches(rule: str, pattern: str) -> bool:
    """Match one exact rule name or one documented glob pattern."""
    return fnmatchcase(rule, pattern)


def _path_matches(file: str, pattern: str, root: Path) -> bool:
    """Match waiver path globs against normalized repo-relative paths."""
    normalized = _normalize_violation_path(file, root)
    return fnmatchcase(normalized, pattern) or fnmatchcase(f"./{normalized}", pattern)


def _normalize_violation_path(file: str, root: Path) -> str:
    """Normalize violation paths to POSIX repo-relative form for matching."""
    path = Path(file)
    if path.is_absolute():
        try:
            path = path.relative_to(root)
        except ValueError:
            pass
    return path.as_posix()


def _value_allowed(violation: Violation, waiver: WaiverConfig) -> bool:
    """Apply the optional local ceiling for a waiver."""
    if waiver.allow_up_to is None:
        return True
    if not isinstance(violation.value, int | float):
        return False
    return violation.value <= waiver.allow_up_to


def _mark_waived(violation: Violation, waiver: WaiverConfig) -> Violation:
    """Attach waiver metadata to a violation copy."""
    metadata = dict(violation.metadata)
    metadata["waiver"] = {
        "id": waiver.id,
        "reason": waiver.reason,
        "allow_up_to": waiver.allow_up_to,
        "expires": waiver.expires,
    }
    return replace(violation, metadata=metadata)
