#!/usr/bin/env python3
"""Compare two ``slop lint --output json`` runs for v2.0 parity gates.

Usage:
    python scripts/diff_results.py old.json new.json

Used by the G2 / G3 parity gates in ``docs/planning/migration.md`` to
verify that the v2 engine produces equivalent findings to the legacy
engine. Output is structural:

  - Rules present in old but not new (or vice versa).
  - Per-rule violation count deltas.
  - Per-rule status deltas (pass/fail/error/skip).
  - Summary deltas (rules_checked, violation_count, advisory_count).

This script does NOT classify diffs as "expected" vs "regression" —
that is human judgment. It prints the raw structural diff for review.
The parity-gate intent (N+1) records the classified outcome in
``docs/research/snapshots/v2_parity_*.md``.

Exit codes:
  0 — files load cleanly (regardless of whether diffs were found).
  1 — usage error or file load failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    """Load a slop JSON output file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def diff_summary(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Return human-readable lines for top-level summary deltas."""
    lines: list[str] = []
    old_sum = old.get("summary", {})
    new_sum = new.get("summary", {})
    for key in sorted(set(old_sum) | set(new_sum)):
        ov, nv = old_sum.get(key), new_sum.get(key)
        if ov != nv:
            lines.append(f"  summary.{key}: {ov!r} -> {nv!r}")
    return lines


def diff_rules(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Return human-readable lines for per-rule structural deltas."""
    lines: list[str] = []
    old_rules = old.get("rules", {})
    new_rules = new.get("rules", {})

    only_old = sorted(set(old_rules) - set(new_rules))
    only_new = sorted(set(new_rules) - set(old_rules))
    common = sorted(set(old_rules) & set(new_rules))

    if only_old:
        lines.append("Rules present in OLD only:")
        for r in only_old:
            lines.append(f"  - {r}")
    if only_new:
        lines.append("Rules present in NEW only:")
        for r in only_new:
            lines.append(f"  + {r}")

    rule_deltas: list[str] = []
    for rule in common:
        old_r = old_rules[rule]
        new_r = new_rules[rule]
        old_status = old_r.get("status")
        new_status = new_r.get("status")
        old_viol_count = len(old_r.get("violations", []))
        new_viol_count = len(new_r.get("violations", []))
        old_waived_count = len(old_r.get("waived_violations", []))
        new_waived_count = len(new_r.get("waived_violations", []))
        if (
            old_status != new_status
            or old_viol_count != new_viol_count
            or old_waived_count != new_waived_count
        ):
            parts = [f"  {rule}:"]
            if old_status != new_status:
                parts.append(f"status {old_status} -> {new_status}")
            if old_viol_count != new_viol_count:
                parts.append(f"violations {old_viol_count} -> {new_viol_count}")
            if old_waived_count != new_waived_count:
                parts.append(f"waived {old_waived_count} -> {new_waived_count}")
            rule_deltas.append(" ".join(parts))
    if rule_deltas:
        lines.append("Per-rule deltas:")
        lines.extend(rule_deltas)
    return lines


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} OLD.json NEW.json", file=sys.stderr)
        return 1
    try:
        old = load(Path(argv[1]))
        new = load(Path(argv[2]))
    except (OSError, json.JSONDecodeError) as e:
        print(f"diff_results: load failed: {e}", file=sys.stderr)
        return 1

    summary_lines = diff_summary(old, new)
    rule_lines = diff_rules(old, new)

    if not summary_lines and not rule_lines:
        print("No structural diffs.")
        return 0

    if summary_lines:
        print("Summary deltas:")
        print("\n".join(summary_lines))
        print()
    if rule_lines:
        print("\n".join(rule_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
