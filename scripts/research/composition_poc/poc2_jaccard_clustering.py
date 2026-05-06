"""PoC 2: Agglomerative Jaccard clustering on identifier token sets.

Algorithm
---------
1. For each top-level function, build a token-set of:
   - function name tokens
   - first parameter name tokens (proxy for "what it operates on")
2. Compute pairwise Jaccard distance over those sets.
3. Run single-linkage agglomerative clustering: merge the two
   closest items / clusters until distance exceeds threshold.
4. Output clusters of size >= 3.

Theoretical basis
-----------------
- Bavota et al., "An Extract Class Refactoring Approach Based on
  Class Cohesion": cohesion-driven decomposition recommendations
  using identifier-similarity clustering.
- Fokaefs et al., "Decomposing Object-Oriented Class Modules Using
  an Agglomerative Clustering Technique": exact algorithm shape.

Note: this PoC uses *single-linkage* (the simplest / most chainy
linkage) so we can reason about the output without bringing in
sklearn. Production use would prefer average or Ward.

Usage
-----
    python poc2_jaccard_clustering.py FILE [FILE ...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DEF_RE = re.compile(
    r"^def\s+(\w+)\s*\(\s*([^),]*)",
    re.MULTILINE,
)
CAMEL_LU = re.compile(r"([a-z])([A-Z])")
CAMEL_UU = re.compile(r"([A-Z]+)([A-Z][a-z])")
PARAM_NAME_RE = re.compile(r"^(\w+)")


def split_identifier(name: str) -> list[str]:
    s = name.strip("_")
    s = CAMEL_LU.sub(r"\1_\2", s)
    s = CAMEL_UU.sub(r"\1_\2", s)
    return [t.lower() for t in re.split(r"[_]+", s) if t]


def collect(paths):
    """Return [(name, path, token_set), ...]."""
    out = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in DEF_RE.finditer(text):
            name = m.group(1)
            first_param = (m.group(2) or "").strip()
            pm = PARAM_NAME_RE.match(first_param)
            first_tokens: list[str] = []
            if pm:
                first_tokens = split_identifier(pm.group(1))
            tokens = set(split_identifier(name)) | set(first_tokens)
            out.append((name, p, tokens))
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return 1 - len(a & b) / len(a | b)


def cluster(items, threshold: float = 0.5) -> list[list[int]]:
    """Single-linkage agglomerative clustering.

    Returns a list of clusters; each cluster is a list of item indices.
    Two clusters merge if any pair across them has distance ≤ threshold.
    """
    n = len(items)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            d = jaccard(items[i][2], items[j][2])
            if d <= threshold:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    return [c for c in clusters.values() if len(c) >= 3]


def report(items, clusters) -> str:
    lines = ["# PoC 2 — Agglomerative Jaccard clustering candidates\n"]
    if not clusters:
        lines.append("_No clusters of size >= 3 at threshold 0.5._\n")
        return "\n".join(lines)
    clusters.sort(key=lambda c: -len(c))
    for idx, cluster_idxs in enumerate(clusters, start=1):
        # Compute cluster's shared tokens
        shared = set.intersection(*(items[i][2] for i in cluster_idxs))
        lines.append(f"## Cluster {idx} ({len(cluster_idxs)} members)\n")
        if shared:
            lines.append(f"**Shared tokens**: " + ", ".join(f"`{t}`" for t in sorted(shared)))
        else:
            lines.append("**Shared tokens**: _(none — chained via overlap, not core overlap)_")
        lines.append("")
        lines.append("| Function | File | All tokens |")
        lines.append("|---|---|---|")
        for i in cluster_idxs:
            name, path, toks = items[i]
            lines.append(
                f"| `{name}` | {path.name} | "
                f"{', '.join(sorted(toks))} |"
            )
        lines.append("")
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    paths = [Path(p) for p in argv[1:]]
    items = collect(paths)
    clusters = cluster(items, threshold=0.5)
    print(report(items, clusters))


if __name__ == "__main__":
    main(sys.argv)
