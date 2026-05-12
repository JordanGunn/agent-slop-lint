"""Rule-execution helpers — selection + waivers + verdict aggregation.

Moved here from the retired ``slop.engine`` module during the deletion
sweep. ``Linter.run`` consumes these; nothing else should import from
this module (it's private to the linter package).
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from fnmatch import fnmatchcase
from pathlib import Path

from slop._compat import canonical_categories, canonical_rule_name
from slop.config.models import WaiverConfig
from slop.linter.types import RuleResult
from slop.linter.slop import Slop


def select_rules(filter_rule, filter_category):
    """Resolve filters to a list of rules to run.

    Legacy rule / category names are translated to canonical form via
    ``slop._compat`` before lookup. Prefix matching is preserved so
    ``slop check structural.class`` still picks up every nested rule.

    Raises ``KeyError(filter)`` if the filter matches no rule or category.
    """
    from slop.linter import RULE_REGISTRY  # local import to avoid cycle

    if filter_rule:
        return _resolve_rule_filter(filter_rule)
    if filter_category:
        return _resolve_category_filter(filter_category)
    return list(RULE_REGISTRY)


def _resolve_rule_filter(filter_rule: str) -> list:
    """Resolve a single-rule (or rule-prefix) filter to its rule set."""
    from slop.linter import RULE_REGISTRY, RULES_BY_NAME

    canonical, _ = canonical_rule_name(filter_rule)
    rule_def = RULES_BY_NAME.get(canonical)
    if rule_def is not None:
        return [rule_def]
    prefix = canonical + "."
    matches = [r for r in RULE_REGISTRY if r.name.startswith(prefix)]
    if matches:
        return matches
    raise KeyError(filter_rule)


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


def _resolve_category_filter(filter_category: str) -> list:
    """Resolve a category filter (canonical or legacy alias) to its rule set."""
    categories, _ = canonical_categories(filter_category)
    matches: list = []
    seen: set[str] = set()
    for cat in categories:
        matches.extend(_rules_for_category(cat, seen))
    if not matches:
        raise KeyError(filter_category)
    return matches


def overall_status(rule_results, total_violations) -> str:
    """Collapse per-rule results into a single error/fail/pass verdict."""
    if any(r.status == "error" for r in rule_results.values()):
        return "error"
    if total_violations > 0:
        return "fail"
    return "pass"


def apply_waivers(
    result: RuleResult,
    waivers: list[WaiverConfig],
    root: Path,
) -> RuleResult:
    """Move matching violations into waived_violations without hiding them."""
    if not waivers or not result.violations:
        return result

    remaining: list[Slop] = []
    waived: list[Slop] = [*result.waived_violations]
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
    violation: Slop,
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
    return waiver.expires is not None and date.fromisoformat(waiver.expires) < today


def _rule_matches(rule: str, pattern: str) -> bool:
    return fnmatchcase(rule, pattern)


def _path_matches(file: str, pattern: str, root: Path) -> bool:
    normalized = _normalize_violation_path(file, root)
    return fnmatchcase(normalized, pattern) or fnmatchcase(f"./{normalized}", pattern)


def _normalize_violation_path(file: str, root: Path) -> str:
    path = Path(file)
    if path.is_absolute():
        try:
            path = path.relative_to(root)
        except ValueError:
            pass
    return path.as_posix()


def _value_allowed(violation: Slop, waiver: WaiverConfig) -> bool:
    if waiver.allow_up_to is None:
        return True
    if not isinstance(violation.value, int | float):
        return False
    return violation.value <= waiver.allow_up_to


def _mark_waived(violation: Slop, waiver: WaiverConfig) -> Slop:
    metadata = dict(violation.metadata)
    metadata["waiver"] = {
        "id": waiver.id,
        "reason": waiver.reason,
        "allow_up_to": waiver.allow_up_to,
        "expires": waiver.expires,
    }
    return replace(violation, metadata=metadata)
