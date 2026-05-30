"""Rule-execution helpers — selection + ignores + verdict aggregation.

Moved here from the retired ``slop.engine`` module during the deletion
sweep. ``Linter.run`` consumes these; nothing else should import from
this module (it's private to the linter package).
"""
from __future__ import annotations

from slop.linter.rule import Rule
from slop.linter.types import RuleResult
from slop.linter.slop import Slop

# Map a finding's ``scope`` to its ignore-list key.
_SCOPE_PLURAL: dict[str, str] = {
    "function": "functions",
    "class": "classes",
    "module": "modules",
    "package": "packages",
}


def select_rules(name, category):
    """Resolve filters to a list of rules to run.

    Prefix matching is preserved so ``slop check class``
    picks up every nested rule.

    Raises ``KeyError(filter)`` if the filter matches no rule or category.
    """
    from slop.linter import RULE_REGISTRY  # local import to avoid cycle

    if name:
        return _resolve_rule_filter(name)
    if category:
        return _resolve_category_filter(category)
    return list(RULE_REGISTRY)


def _resolve_rule_filter(name: str) -> list:
    """Resolve a single-rule (or rule-prefix) filter to its rule set."""
    from slop.linter import RULE_REGISTRY, RULES_BY_NAME

    rule_def = RULES_BY_NAME.get(name)
    if rule_def is not None:
        return [rule_def]
    prefix = name + "."
    matches = [r for r in RULE_REGISTRY if r.name.startswith(prefix)]
    if matches:
        return matches
    raise KeyError(name)


def _rules_for_category(category: str, seen: set[str]) -> list:
    """Append direct + nested-prefix + by-name matches for one category."""
    from slop.linter import RULE_REGISTRY, RULES_BY_CATEGORY, RULES_BY_NAME

    matches: list = []
    for rule in RULES_BY_CATEGORY.get(category, []):
        if rule.name not in seen:
            matches.append(rule)
            seen.add(rule.name)
    by_name = RULES_BY_NAME.get(category)
    if by_name is not None and by_name.name not in seen:
        matches.append(by_name)
        seen.add(by_name.name)
    prefix = category + "."
    for rule in RULE_REGISTRY:
        if rule.category.startswith(prefix) and rule.name not in seen:
            matches.append(rule)
            seen.add(rule.name)
    return matches


def _resolve_category_filter(category: str) -> list:
    """Resolve a category filter to its rule set."""
    matches = _rules_for_category(category, set())
    if not matches:
        raise KeyError(category)
    return matches


def overall_status(rule_results, total_violations) -> str:
    """Collapse per-rule results into a single error/fail/pass verdict."""
    if any(r.status == "error" for r in rule_results.values()):
        return "error"
    if total_violations > 0:
        return "fail"
    return "pass"


def apply_ignores(
    result: RuleResult,
    rule_config: Rule,
    global_ignore: dict[str, list[str]],
) -> RuleResult:
    """Drop findings whose declared name is in an ignore list for its scope.

    A finding is suppressed when its ``symbol`` appears in the union of the
    global ``[ignore]`` table and this rule's ``[rules.<rule>.ignore]`` for
    the finding's scope. Scope-precise: ignoring a class never blinds its
    methods. Silent: suppressed findings are dropped, not surfaced — the
    exemption lives auditably in the config, not in the output.
    """
    if not result.violations:
        return result
    rule_ignore = rule_config.params.get("ignore", {}) or {}
    if not global_ignore and not rule_ignore:
        return result

    kept: list[Slop] = []
    for v in result.violations:
        plural = _SCOPE_PLURAL.get(v.scope or "")
        if plural is not None and v.symbol is not None:
            ignored = set(global_ignore.get(plural, ())) | set(rule_ignore.get(plural, ()))
            if v.symbol in ignored:
                continue
        kept.append(v)

    result.violations = kept
    result.summary["violation_count"] = len(kept)
    return result
