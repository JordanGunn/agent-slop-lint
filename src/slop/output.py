"""Output formatters for slop.

Supports human-readable (default), quiet (summary only), and JSON output.
"""

from __future__ import annotations

import json

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

    # Group rule results by category (preserve insertion order)
    categories: dict[str, list[tuple[str, RuleResult]]] = {}
    for rule_name, rr in result.rule_results.items():
        cat = rule_name.split(".")[0] if "." in rule_name else rule_name
        categories.setdefault(cat, []).append((rule_name, rr))

    for cat, rule_pairs in categories.items():
        all_skipped = all(rr.status == "skip" for _, rr in rule_pairs)

        if all_skipped:
            lines.append(dim(f"{cat} (disabled)"))
            lines.append(dim(f"  \u2139 skipped (enable in .slop.toml)"))
            lines.append("")
            continue

        # Category header with context
        header_extras = _category_header_extras(rule_pairs)
        header_suffix = f" ({', '.join(header_extras)})" if header_extras else ""
        lines.append(bold(f"{cat}{header_suffix}"))

        # Group violations by sub-rule
        cat_total_violations = 0
        cat_checked = 0
        has_multiple_rules = len([rp for rp in rule_pairs if rp[1].status != "skip"]) > 1

        for rule_name, rr in rule_pairs:
            if rr.status == "skip":
                continue

            violations = rr.violations
            cat_total_violations += len(violations)

            # Extract checked count
            for key in ("functions_checked", "files_analyzed", "packages_analyzed", "classes_checked"):
                if key in rr.summary:
                    cat_checked = max(cat_checked, rr.summary[key])

            if not violations:
                continue

            # Sub-rule header (only if category has multiple rules)
            if has_multiple_rules:
                sub_name = rule_name.split(".", 1)[1] if "." in rule_name else rule_name
                lines.append(f"  {sub_name}")
                indent = "    "
            else:
                indent = "  "

            # Show violations (capped)
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
                lines.append("")  # blank between sub-rules

        # Category summary
        checked_str = f", {cat_checked} checked" if cat_checked else ""
        if cat_total_violations > 0:
            lines.append(f"  {_plural(cat_total_violations, 'violation')}{checked_str}")
        else:
            lines.append(f"  {green('\u2713')} clean{checked_str}")

        lines.append("")

    # Footer
    lines.append("\u2500" * 40)
    lines.append(_format_footer(result))

    return "\n".join(lines)


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
