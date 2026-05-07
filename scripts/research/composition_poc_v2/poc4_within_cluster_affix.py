"""PoC v2.4 — Within-cluster affix re-detection.

For each first-parameter cluster, run the existing affix-pattern
detection on the cluster's MEMBER FUNCTION NAMES. If the names
themselves form a closed-alphabet pattern, the cluster has a clear
varying token; if not, it's a bag of helpers sharing input.

This composes detection: first-parameter clustering finds the
candidate group, then affix detection within tells you whether
it's a clean dispatch family with a named alphabet, or just
incidentally co-occurring helpers.

Theoretical grounding
---------------------
- Caprile & Tonella (2000) — identifier-pattern restructuring;
  applied here at finer scope (within an already-clustered group).
- Wille (1982) FCA — already used by slop's affix kernel.

Usage
-----
    cd src
    uv run python ../scripts/research/composition_poc_v2/poc4_within_cluster_affix.py cli/slop
"""
from __future__ import annotations

import sys
from pathlib import Path

from slop._structural.composition import (
    _build_affix_patterns,
    _split,
    first_parameter_drift_kernel,
)


def main(root: str) -> None:
    print("# PoC v2.4 — Within-cluster affix re-detection")
    print()
    rp = Path(root)
    drift_result = first_parameter_drift_kernel(rp, languages=["python"])

    print(f"Root: `{root}`  |  Clusters: {len(drift_result.clusters)}")
    print()
    print("| Cluster (param) | Scope | Members | Affix patterns within | Coverage |")
    print("|---|---|---|---|---|")

    detail_rows: list[tuple] = []
    for c in drift_result.clusters:
        if c.verdict != "strong":
            continue
        # Build (name, file, line, tokens) tuples for the cluster's members
        items = [
            (name, file, line, _split(name))
            for name, file, line in c.members
        ]
        patterns = _build_affix_patterns(items)
        # Filter to patterns that cover ≥ 2 cluster members
        meaningful = [p for p in patterns if sum(len(v) for v in p.variants.values()) >= 2]

        # Compute coverage: fraction of cluster members in any pattern
        covered = set()
        for p in meaningful:
            for entity, members in p.variants.items():
                for n, _, _ in members:
                    covered.add(n)
        coverage = len(covered) / len(items) if items else 0.0

        if meaningful:
            stems_repr = "; ".join(
                "_".join(t for t in p.stem)
                + f" → {{{', '.join(sorted(p.variants.keys()))}}}"
                for p in meaningful[:2]
            )
            if len(meaningful) > 2:
                stems_repr += f" (+{len(meaningful) - 2})"
        else:
            stems_repr = "—"
        print(
            f"| `{c.parameter_name}` | `{c.scope}` | {len(items)} | "
            f"{stems_repr} | {coverage:.0%} |"
        )
        detail_rows.append((c, items, meaningful, coverage))

    print()
    print("## Per-cluster detail")
    print()
    for c, items, patterns, coverage in detail_rows:
        names = [n for n, _, _ in c.members]
        print(f"### `{c.parameter_name}` in `{c.scope}` (coverage {coverage:.0%})")
        print()
        print(f"- Members: {', '.join(f'`{n}`' for n in names)}")
        if patterns:
            print(f"- Affix patterns ({len(patterns)}):")
            for p in patterns:
                stem = "_".join(p.stem)
                print(f"  - stem `{stem}`, alphabet `{sorted(p.variants.keys())}`")
        else:
            print("- _No affix pattern within cluster — heterogeneous helpers._")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
