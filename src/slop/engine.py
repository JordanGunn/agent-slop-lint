"""Rule execution engine for slop.

Iterates enabled rules, calls their run functions, collects results,
and computes the aggregate lint result with exit code.
"""

from __future__ import annotations

from pathlib import Path

from slop import __version__
from slop.models import LintResult, RuleResult, SlopConfig
from slop.rules import RULE_REGISTRY, RULES_BY_CATEGORY, RULES_BY_NAME


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
    rule_results: dict[str, RuleResult] = {}
    rules_checked = 0
    rules_skipped = 0
    total_violations = 0
    total_advisories = 0

    # Determine which rules to run
    if filter_rule:
        rule_def = RULES_BY_NAME.get(filter_rule)
        if rule_def is not None:
            rules_to_run = [rule_def]
        else:
            # Try prefix match (subcategory, e.g. "class.inheritance")
            prefix = filter_rule + "."
            prefix_matches = [r for r in RULE_REGISTRY if r.name.startswith(prefix)]
            if prefix_matches:
                rules_to_run = prefix_matches
            else:
                return LintResult(
                    version=__version__,
                    root=str(root),
                    languages=config.languages,
                    result="error",
                    rule_results={
                        filter_rule: RuleResult(
                            rule=filter_rule,
                            status="error",
                            errors=[f"Unknown rule: {filter_rule}"],
                        )
                    },
                )
    elif filter_category:
        rules_to_run = RULES_BY_CATEGORY.get(filter_category, [])
        if not rules_to_run:
            return LintResult(
                version=__version__,
                root=str(root),
                languages=config.languages,
                result="error",
                rule_results={
                    filter_category: RuleResult(
                        rule=filter_category,
                        status="error",
                        errors=[f"Unknown category: {filter_category}"],
                    )
                },
            )
    else:
        rules_to_run = list(RULE_REGISTRY)

    # Execute each rule
    for rule_def in rules_to_run:
        rc = config.rule_config(rule_def.category)

        # Check if rule is enabled
        if not rc.enabled or rc.severity == "off":
            rule_results[rule_def.name] = RuleResult(
                rule=rule_def.name, status="skip"
            )
            rules_skipped += 1
            continue

        # Run the rule
        try:
            result = rule_def.run(root, rc, config)
        except Exception as e:
            result = RuleResult(
                rule=rule_def.name,
                status="error",
                errors=[f"{type(e).__name__}: {e}"],
            )

        # A rule that produced errors but no violations should be reported
        # as an error, not a pass — otherwise silent failures (e.g. missing
        # binaries, unreadable files) render as clean.
        if result.errors and result.status == "pass":
            result.status = "error"

        rule_results[rule_def.name] = result
        rules_checked += 1

        # Count violations vs advisories
        for v in result.violations:
            if v.severity in ("error",):
                total_violations += 1
            else:
                total_advisories += 1

    # Determine overall result
    if any(r.status == "error" for r in rule_results.values()):
        overall = "error"
    elif total_violations > 0:
        overall = "fail"
    else:
        overall = "pass"

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
        result=overall,
    )
