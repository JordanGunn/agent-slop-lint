"""Rule execution engine for slop.

Iterates enabled rules, calls their run functions, collects results,
and computes the aggregate lint result with exit code.
"""

from __future__ import annotations

from pathlib import Path

from slop import __version__
from slop.models import LintResult, RuleResult, SlopConfig
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

    for rule_def in rules_to_run:
        rc = config.rule_config(rule_def.category)
        if not rc.enabled or rc.severity == "off":
            rule_results[rule_def.name] = RuleResult(rule=rule_def.name, status="skip")
            rules_skipped += 1
            continue

        result = _execute_rule(rule_def, root, rc, config)
        rule_results[rule_def.name] = result
        rules_checked += 1

        for v in result.violations:
            if v.severity == "error":
                total_violations += 1
            else:
                total_advisories += 1

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
        result=_overall_status(rule_results, total_violations),
    )


def _overall_status(rule_results, total_violations) -> str:
    """Collapse per-rule results into a single error/fail/pass verdict."""
    if any(r.status == "error" for r in rule_results.values()):
        return "error"
    if total_violations > 0:
        return "fail"
    return "pass"
