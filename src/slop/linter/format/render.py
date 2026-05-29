"""Human-readable render helpers for the format subpackage.

Companion to ``format.__init__`` which exposes the three public output
surfaces: ``human``, ``quiet``, ``as_dict``. This module holds the
rendering machinery that builds the human-readable output — category
grouping, finding rendering, summary aggregation, footer composition.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from slop.cli.color import bold, dim, green, red, yellow

# Observation glyph (U+2139 INFORMATION SOURCE) — distinct from the ✗/⚠
# verdict markers so a claim-free nudge never reads as a defect.
_INFO_GLYPH = "ℹ"
from slop.linter.result import Result
from slop.linter.types import RuleResult
from slop.linter.slop import Slop

# Default number of violations shown per sub-rule before "...and N more"
DEFAULT_MAX_VIOLATIONS = 5


def _category_for(rule_name: str) -> str:
    """Return the category a rule belongs to.

    Falls back to the rule name itself when the rule isn't registered
    (covers test fixtures that monkey-patch the registry).
    """
    from slop.linter import RULES_BY_NAME
    rule_def = RULES_BY_NAME.get(rule_name)
    if rule_def is not None:
        return rule_def.category
    return rule_name


def _short_name_for(rule_name: str) -> str:
    """Return the leaf segment of a rule name for display under its category."""
    if "." in rule_name:
        return rule_name.rsplit(".", 1)[1]
    return rule_name


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    """Return '1 violation' or '53 violations'."""
    if plural is None:
        plural = singular + "s"
    return f"{n} {singular}" if n == 1 else f"{n} {plural}"


# ---------------------------------------------------------------------------
# Human-readable
# ---------------------------------------------------------------------------


def human(result: Result, *, max_violations: int = DEFAULT_MAX_VIOLATIONS) -> str:
    """Format a Result as human-readable terminal output."""
    lines: list[str] = []
    display = result.display_root or result.root
    lines.append(bold(f"slop {result.version}") + f" \u2014 scanning {display}")
    lines.append("")

    for cat, rule_pairs in _group_by_category(result).items():
        lines.extend(_render_category(cat, rule_pairs, max_violations))

    lines.append("\u2500" * 40)
    lines.append(_format_footer(result))
    return "\n".join(lines)


def _group_by_category(
    result: Result,
) -> dict[str, list[tuple[str, RuleResult]]]:
    """Group rule results by registered category, preserving insertion order."""
    categories: dict[str, list[tuple[str, RuleResult]]] = {}
    for rule_name, rr in result.rule_results.items():
        cat = _category_for(rule_name)
        categories.setdefault(cat, []).append((rule_name, rr))
    return categories


def _render_category(
    cat: str,
    rule_pairs: list[tuple[str, RuleResult]],
    max_violations: int,
) -> list[str]:
    """Render one category block: header, violations, errors, summary."""
    if all(rr.status == "skip" for _, rr in rule_pairs):
        return [
            dim(f"{cat} (disabled)"),
            dim("  \u2139 skipped (enable in .slop.toml)"),
            "",
        ]

    lines: list[str] = []
    header_extras = _category_header_extras(rule_pairs)
    header_suffix = f" ({', '.join(header_extras)})" if header_extras else ""
    lines.append(bold(f"{cat}{header_suffix}"))

    has_multiple_rules = sum(1 for _, rr in rule_pairs if rr.status != "skip") > 1
    agg = _aggregate_category(rule_pairs)

    lines.extend(_render_category_findings(rule_pairs, has_multiple_rules, max_violations))
    lines.extend(_render_observations(rule_pairs, has_multiple_rules))

    # Errors (missing binaries, unreadable files, git failures, …) — surfaced
    # here so silent failures can't render as ✓ clean the way they used to.
    for rule_name, err in agg.errors:
        sub_name = _short_name_for(rule_name)
        prefix = f"{sub_name}: " if has_multiple_rules else ""
        lines.append(f"  {red(chr(0x2717))} {prefix}{err}")

    lines.append(_category_summary_line(agg))
    lines.append("")
    return lines


def _render_category_findings(
    rule_pairs: list[tuple[str, RuleResult]],
    has_multiple_rules: bool,
    max_violations: int,
) -> list[str]:
    """Render failing findings first, then waived findings."""
    lines: list[str] = []
    for rule_name, rr in _rules_where(rule_pairs, "violations"):
        lines.extend(_render_violations(
            rule_name, rr.violations, has_multiple_rules, max_violations,
        ))
    for rule_name, rr in _rules_where(rule_pairs, "waived_violations"):
        lines.extend(_render_waived(
            rule_name, rr.waived_violations, has_multiple_rules, max_violations,
        ))
    return lines


def _render_observations(
    rule_pairs: list[tuple[str, RuleResult]],
    has_multiple_rules: bool,
) -> list[str]:
    """Render claim-free observations: ℹ marker + the narration prose.

    Observations carry no defect, so they render distinctly from
    violations and are never capped — there is typically one per rule.
    """
    lines: list[str] = []
    for rule_name, rr in _rules_where(rule_pairs, "observations"):
        indent = "  "
        if has_multiple_rules:
            lines.append(f"  {_short_name_for(rule_name)}")
            indent = "    "
        for ob in rr.observations:
            lines.append(f"{indent}{dim(_INFO_GLYPH)} {ob.message}")
    return lines


def _rules_where(
    rule_pairs: list[tuple[str, RuleResult]],
    attr: str,
) -> list[tuple[str, RuleResult]]:
    """Return non-skipped rule results whose ``attr`` attribute is truthy.

    ``attr`` is one of ``"violations"`` or ``"waived_violations"`` — the
    two finding-list fields callers want to iterate over.
    """
    return [
        (rule_name, rr)
        for rule_name, rr in rule_pairs
        if rr.status != "skip" and getattr(rr, attr)
    ]


@dataclass
class _CategoryAgg:
    """Aggregated metrics for one category across all its sub-rules."""

    total_violations: int = 0
    total_waived: int = 0
    total_observations: int = 0
    checked: int = 0
    ran_rules: int = 0
    has_count: bool = False
    errors: list[tuple[str, str]] = field(default_factory=list)
    has_error_status: bool = False


# A rule reports how many units it examined via any summary key with one
# of these suffixes (functions_checked, files_analyzed, candidates_analyzed,
# …). Convention over allowlist: a hardcoded key list silently drops every
# new count key — the same source-of-truth drift that hid the complexity
# no-op. The suffix is the single source of truth.
_COUNT_SUFFIXES = ("_checked", "_analyzed", "_scanned", "_examined", "_searched")


def _checked_count(summary: dict) -> int | None:
    """Largest unit-count a rule's summary reports, or None if it reports none.

    ``None`` ("rule never reports a count") is distinct from ``0`` ("rule
    ran and examined nothing") — the latter is the misconfiguration signal.
    """
    counts = [
        v for k, v in summary.items()
        if isinstance(v, int) and k.endswith(_COUNT_SUFFIXES)
    ]
    return max(counts) if counts else None


def _aggregate_category(rule_pairs: list[tuple[str, RuleResult]]) -> _CategoryAgg:
    """Fold a category's rule results into a single summary record."""
    agg = _CategoryAgg()
    for rule_name, rr in rule_pairs:
        if rr.status == "skip":
            continue
        agg.ran_rules += 1
        agg.total_violations += len(rr.violations)
        agg.total_waived += len(rr.waived_violations)
        agg.total_observations += len(rr.observations)
        if rr.status == "error":
            agg.has_error_status = True
        for err in rr.errors:
            agg.errors.append((rule_name, err))
        cnt = _checked_count(rr.summary)
        if cnt is not None:
            agg.has_count = True
            agg.checked = max(agg.checked, cnt)
    return agg


def _render_violations(
    rule_name: str,
    violations: list[Slop],
    has_multiple_rules: bool,
    max_violations: int,
) -> list[str]:
    """Render the violation block for one sub-rule."""
    lines: list[str] = []
    if has_multiple_rules:
        sub_name = _short_name_for(rule_name)
        lines.append(f"  {sub_name}")
        indent = "    "
    else:
        indent = "  "

    shown = violations[:max_violations]
    for v in shown:
        marker = red("\u2717") if v.severity == "error" else yellow("\u26a0")
        scope_tag = dim(f"[{v.scope}] ") if v.scope else ""
        loc = v.file
        if v.line:
            loc += f":{v.line}"
        if v.symbol:
            loc += f" {v.symbol}"
        lines.append(f"{indent}{marker} {scope_tag}{loc} \u2014 {v.message}")

    remaining = len(violations) - len(shown)
    if remaining > 0:
        lines.append(dim(f"{indent}...and {remaining} more"))

    if has_multiple_rules:
        lines.append("")
    return lines


def _render_waived(
    rule_name: str,
    violations: list[Slop],
    has_multiple_rules: bool,
    max_violations: int,
) -> list[str]:
    """Render waived findings for one sub-rule."""
    lines: list[str] = []
    if has_multiple_rules:
        sub_name = _short_name_for(rule_name)
        lines.append(f"  {sub_name} waived")
        indent = "    "
    else:
        lines.append("  waived")
        indent = "    "

    shown = violations[:max_violations]
    for v in shown:
        loc = v.file
        if v.line:
            loc += f":{v.line}"
        if v.symbol:
            loc += f" {v.symbol}"
        waiver = v.metadata.get("waiver", {})
        waiver_id = waiver.get("id", "unknown-waiver")
        reason = waiver.get("reason", "")
        lines.append(
            f"{indent}{yellow(chr(0x26a0))} {loc} \u2014 {v.message} "
            f"(waived by {waiver_id})"
        )
        if reason:
            lines.append(dim(f"{indent}  reason: {reason}"))

    remaining = len(violations) - len(shown)
    if remaining > 0:
        lines.append(dim(f"{indent}...and {remaining} more waived"))

    if has_multiple_rules:
        lines.append("")
    return lines


def _category_summary_line(agg: _CategoryAgg) -> str:
    """Pick the right one-line summary (errors > violations > zero-check > clean)."""
    checked_str = f", {agg.checked} checked" if agg.checked else ""
    if agg.has_error_status or agg.errors:
        cross = red("\u2717")
        count = max(len(agg.errors), 1)
        noun = "error" if count == 1 else "errors"
        return f"  {cross} {count} {noun}{checked_str}"
    if agg.total_violations > 0:
        suffix = f", {_plural(agg.total_waived, 'waived', 'waived')}" if agg.total_waived else ""
        return f"  {_plural(agg.total_violations, 'violation')}{suffix}{checked_str}"
    if agg.total_waived > 0:
        return f"  {yellow(_plural(agg.total_waived, 'waived', 'waived'))}{checked_str}"
    # Observation-only category (no verdicts): report the nudge, not "clean".
    # Observations make no defect claim, so this is not a pass/fail signal.
    if agg.total_observations > 0:
        noun = "observation" if agg.total_observations == 1 else "observations"
        return f"  {dim(_INFO_GLYPH)} {agg.total_observations} {noun}{checked_str}"
    # A rule that ran and reported a count of 0 examined nothing despite
    # being enabled \u2014 almost always a wiring/config error (the bug that
    # hid the complexity family), NOT a clean pass. Make it loud.
    if agg.ran_rules > 0 and agg.has_count and agg.checked == 0:
        return (
            f"  {red(chr(0x2717))} examined 0 units \u2014 "
            f"enabled but nothing checked (likely misconfiguration)"
        )
    # Ran but reported no count key at all \u2014 can't assert it checked
    # nothing, so don't cry wolf; report clean.
    return f"  {green(chr(0x2713))} clean{checked_str}"


def _category_header_extras(rule_pairs: list[tuple[str, RuleResult]]) -> list[str]:
    """Extract contextual info for the category header line."""
    extras: list[str] = []
    for _, rr in rule_pairs:
        if not rr.summary:
            continue
        if "window_since" in rr.summary:
            extras.append(rr.summary["window_since"])
        if "total_commits" in rr.summary:
            extras.append(f"{rr.summary['total_commits']} commits")
        if "languages" in rr.summary and isinstance(rr.summary["languages"], list):
            extras.append(", ".join(rr.summary["languages"]))
    return extras


def _zero_checked_rules(result: Result) -> list[str]:
    """Rules that ran (not skipped) yet reported examining 0 units.

    A reported count of exactly 0 is the misconfiguration tell; a rule
    that reports no count at all is excluded (can't claim it did nothing).
    """
    out: list[str] = []
    for name, rr in result.rule_results.items():
        if rr.status == "skip":
            continue
        if _checked_count(rr.summary) == 0:
            out.append(name)
    return out


def _format_footer(result: Result) -> str:
    """Format the summary footer line."""
    parts: list[str] = []
    if result.slop_count > 0:
        parts.append(red(_plural(result.slop_count, "violation")))
    if result.advisory_count > 0:
        parts.append(yellow(_plural(result.advisory_count, "advisory", "advisories")))
    if result.waived_count > 0:
        parts.append(yellow(_plural(result.waived_count, "waived", "waived")))
    if not parts:
        parts.append(green("no violations"))
    if result.observation_count > 0:
        noun = "observation" if result.observation_count == 1 else "observations"
        parts.append(dim(f"{result.observation_count} {noun}"))
    parts.append(_plural(result.rules_checked, "rule") + " checked")
    zero_checked = _zero_checked_rules(result)
    if zero_checked:
        parts.append(red(f"{len(zero_checked)} examined 0 units"))

    status = result.verdict.upper()
    if status == "FAIL":
        status = red(bold("FAIL"))
    elif status == "PASS":
        status = green(bold("PASS"))
    elif status == "ERROR":
        status = red(bold("ERROR"))

    return " | ".join(parts) + f" | {status}"


