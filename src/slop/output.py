"""Output formatters for slop.

Supports human-readable (default), quiet (summary only), and JSON output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from slop.color import bold, dim, green, red, yellow
from slop.models import LintResult, RuleResult, Violation

# Default number of violations shown per sub-rule before "...and N more"
DEFAULT_MAX_VIOLATIONS = 5


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    """Return '1 violation' or '53 violations'."""
    if plural is None:
        plural = singular + "s"
    return f"{n} {singular}" if n == 1 else f"{n} {plural}"


# ---------------------------------------------------------------------------
# Human-readable
# ---------------------------------------------------------------------------


def format_human(result: LintResult, *, max_violations: int = DEFAULT_MAX_VIOLATIONS) -> str:
    """Format a LintResult as human-readable terminal output."""
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
    result: LintResult,
) -> dict[str, list[tuple[str, RuleResult]]]:
    """Group rule results by top-level category, preserving insertion order."""
    categories: dict[str, list[tuple[str, RuleResult]]] = {}
    for rule_name, rr in result.rule_results.items():
        cat = rule_name.split(".")[0] if "." in rule_name else rule_name
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

    # Violations first (skip sub-rules with no violations).
    for rule_name, rr in rule_pairs:
        if rr.status == "skip" or not rr.violations:
            continue
        lines.extend(_render_violations(rule_name, rr.violations, has_multiple_rules, max_violations))

    # Errors (missing binaries, unreadable files, git failures, …) — surfaced
    # here so silent failures can't render as ✓ clean the way they used to.
    for rule_name, err in agg.errors:
        sub_name = rule_name.split(".", 1)[1] if "." in rule_name else rule_name
        prefix = f"{sub_name}: " if has_multiple_rules else ""
        lines.append(f"  {red(chr(0x2717))} {prefix}{err}")

    lines.append(_category_summary_line(agg))
    lines.append("")
    return lines


@dataclass
class _CategoryAgg:
    """Aggregated metrics for one category across all its sub-rules."""

    total_violations: int = 0
    checked: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    has_error_status: bool = False


_CHECKED_KEYS = (
    "functions_checked", "files_analyzed",
    "packages_analyzed", "classes_checked",
)


def _aggregate_category(rule_pairs: list[tuple[str, RuleResult]]) -> _CategoryAgg:
    """Fold a category's rule results into a single summary record."""
    agg = _CategoryAgg()
    for rule_name, rr in rule_pairs:
        if rr.status == "skip":
            continue
        agg.total_violations += len(rr.violations)
        if rr.status == "error":
            agg.has_error_status = True
        for err in rr.errors:
            agg.errors.append((rule_name, err))
        for key in _CHECKED_KEYS:
            if key in rr.summary:
                agg.checked = max(agg.checked, rr.summary[key])
    return agg


def _render_violations(
    rule_name: str,
    violations: list[Violation],
    has_multiple_rules: bool,
    max_violations: int,
) -> list[str]:
    """Render the violation block for one sub-rule."""
    lines: list[str] = []
    if has_multiple_rules:
        sub_name = rule_name.split(".", 1)[1] if "." in rule_name else rule_name
        lines.append(f"  {sub_name}")
        indent = "    "
    else:
        indent = "  "

    shown = violations[:max_violations]
    for v in shown:
        marker = red("\u2717") if v.severity == "error" else yellow("\u26a0")
        loc = v.file
        if v.line:
            loc += f":{v.line}"
        if v.symbol:
            loc += f" {v.symbol}"
        lines.append(f"{indent}{marker} {loc} \u2014 {v.message}")

    remaining = len(violations) - len(shown)
    if remaining > 0:
        lines.append(dim(f"{indent}...and {remaining} more"))

    if has_multiple_rules:
        lines.append("")
    return lines


def _category_summary_line(agg: _CategoryAgg) -> str:
    """Pick the right one-line summary (errors > violations > no-files > clean)."""
    checked_str = f", {agg.checked} checked" if agg.checked else ""
    if agg.has_error_status or agg.errors:
        cross = red("\u2717")
        count = max(len(agg.errors), 1)
        noun = "error" if count == 1 else "errors"
        return f"  {cross} {count} {noun}{checked_str}"
    if agg.total_violations > 0:
        return f"  {_plural(agg.total_violations, 'violation')}{checked_str}"
    if agg.checked == 0:
        return f"  {yellow(chr(0x26a0))} no files matched"
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


def _format_footer(result: LintResult) -> str:
    """Format the summary footer line."""
    parts: list[str] = []
    if result.violation_count > 0:
        parts.append(red(_plural(result.violation_count, "violation")))
    if result.advisory_count > 0:
        parts.append(yellow(_plural(result.advisory_count, "advisory", "advisories")))
    if not parts:
        parts.append(green("no violations"))
    parts.append(_plural(result.rules_checked, "rule") + " checked")

    status = result.result.upper()
    if status == "FAIL":
        status = red(bold("FAIL"))
    elif status == "PASS":
        status = green(bold("PASS"))
    elif status == "ERROR":
        status = red(bold("ERROR"))

    return " | ".join(parts) + f" | {status}"


# ---------------------------------------------------------------------------
# Quiet mode (summary only)
# ---------------------------------------------------------------------------


def format_quiet(result: LintResult) -> str:
    """One-line summary output."""
    return _format_footer(result)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def format_json(result: LintResult) -> str:
    """Format a LintResult as JSON."""
    output: dict = {
        "version": result.version,
        "root": result.root,
        "languages": result.languages,
        "rules": {},
        "summary": {
            "rules_checked": result.rules_checked,
            "rules_skipped": result.rules_skipped,
            "violation_count": result.violation_count,
            "advisory_count": result.advisory_count,
            "result": result.result,
        },
    }

    for rule_name, rr in result.rule_results.items():
        violations_out = []
        for v in rr.violations:
            violations_out.append({
                "rule": v.rule,
                "file": v.file,
                "line": v.line,
                "symbol": v.symbol,
                "message": v.message,
                "severity": v.severity,
                "value": v.value,
                "threshold": v.threshold,
                "metadata": v.metadata,
            })
        output["rules"][rule_name] = {
            "status": rr.status,
            "violations": violations_out,
            "summary": rr.summary,
            "errors": rr.errors,
        }

    return json.dumps(output, indent=2)
