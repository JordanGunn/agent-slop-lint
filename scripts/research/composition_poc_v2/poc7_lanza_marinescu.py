"""PoC v2.7 — Lanza/Marinescu detection-strategy approach.

Compose existing slop primitives into an Extract Class detection
rule, in the spirit of Lanza & Marinescu's *Object-Oriented Metrics
in Practice* (2006). Their framework: build detection rules by
combining multiple metrics with calibrated thresholds, e.g.

    GodClass = (WMC ≥ very_high)
               AND (TCC < 1/3)
               AND (ATFD > few)

For Extract Class on slop's corpus (which is mostly module-level
free functions, not classes), the analog at module scope is:

    ExtractClassCandidate(module) =
        (function_count ≥ moderate)              -- god-module signal
        AND (≥ 2 distinct first-param clusters)  -- multiple receivers in same file
        AND (cluster sizes ≥ small_cluster)      -- each cluster non-trivial

This PoC computes the rule per Python file and reports candidates.
The rule is intentionally simple — Lanza/Marinescu's methodology
is to start from explicit composition of measurable thresholds and
calibrate empirically.

Theoretical grounding
---------------------
- Lanza & Marinescu (2006) *Object-Oriented Metrics in Practice*.
  The book that defined "detection strategies" as composed metric
  rules. Chapter 5 covers Extract Class.
- Marinescu (2004) "Detection Strategies: Metrics-Based Rules for
  Detecting Design Flaws" — the academic-paper precursor.

Usage
-----
    cd src
    uv run python ../scripts/research/composition_poc_v2/poc7_lanza_marinescu.py cli/slop
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from slop._lexical._naming import enumerate_functions
from slop._structural.composition import (
    _classify_cluster,
    _extract_first_param,
)


# Thresholds — the Lanza/Marinescu methodology requires explicit
# calibration; these are starting points for slop's corpus and
# would be tuned empirically.
T_MIN_FUNCTIONS_PER_MODULE = 5      # function_count ≥ moderate
T_MIN_CLUSTERS_PER_MODULE = 2       # ≥ 2 distinct receivers
T_MIN_CLUSTER_SIZE = 3              # each cluster non-trivial


def main(root: str) -> None:
    print("# PoC v2.7 — Lanza/Marinescu-style detection strategy")
    print()
    rp = Path(root)

    # Per-file: count functions; group by first-param name
    functions_per_file: dict[str, list] = defaultdict(list)
    for ctx in enumerate_functions(rp, languages=["python"]):
        if ctx.name.startswith("<"):
            continue
        pname, ptype = _extract_first_param(ctx)
        functions_per_file[ctx.file].append({
            "name": ctx.name,
            "line": ctx.line,
            "param_name": pname,
            "param_type": ptype,
        })

    print(f"Root: `{root}`  |  Files: {len(functions_per_file)}")
    print()
    print("## Detection rule")
    print()
    print(f"```")
    print(f"ExtractClassCandidate(module) =")
    print(f"    (function_count ≥ {T_MIN_FUNCTIONS_PER_MODULE})")
    print(f"    AND (cluster_count ≥ {T_MIN_CLUSTERS_PER_MODULE})")
    print(f"    AND (each cluster size ≥ {T_MIN_CLUSTER_SIZE})")
    print(f"```")
    print()
    print("| File | # Functions | # Clusters (size ≥ 3) | Strong-cluster receivers | Verdict |")
    print("|---|---|---|---|---|")

    candidates: list[tuple] = []
    for file, fns in sorted(functions_per_file.items()):
        if len(fns) < T_MIN_FUNCTIONS_PER_MODULE:
            continue
        # Group by first-param name (skip self/cls/None)
        by_param: dict[str, list] = defaultdict(list)
        for fn in fns:
            pname = fn["param_name"]
            if pname is None or pname in ("self", "cls") or len(pname) < 2:
                continue
            by_param[pname].append(fn)
        clusters = {p: members for p, members in by_param.items()
                    if len(members) >= T_MIN_CLUSTER_SIZE}
        n_clusters = len(clusters)

        # Classify each cluster
        strong_receivers: list[str] = []
        for pname, members in clusters.items():
            types = {fn["param_type"] for fn in members if fn["param_type"]}
            verdict, _ = _classify_cluster(pname, types, frozenset())
            if verdict == "strong":
                strong_receivers.append(pname)

        is_candidate = (
            len(fns) >= T_MIN_FUNCTIONS_PER_MODULE
            and n_clusters >= T_MIN_CLUSTERS_PER_MODULE
        )
        verdict_str = "**candidate**" if is_candidate else "—"
        receivers_str = ", ".join(f"`{r}`" for r in strong_receivers) or "—"
        print(f"| `{file}` | {len(fns)} | {n_clusters} | {receivers_str} | {verdict_str} |")

        if is_candidate:
            candidates.append((file, len(fns), clusters, strong_receivers))

    print()
    print(f"## Candidates: {len(candidates)} file(s)")
    print()
    for file, n_fns, clusters, receivers in candidates:
        print(f"### `{file}` ({n_fns} functions)")
        print()
        for pname, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
            verdict_marker = "STRONG" if pname in receivers else "weak/false-positive"
            member_names = ", ".join(f"`{m['name']}`" for m in members[:5])
            if len(members) > 5:
                member_names += f" (+{len(members) - 5})"
            print(f"- `{pname}` ({len(members)} members, {verdict_marker}): {member_names}")
        print()
        if len(receivers) >= 2:
            print(f"_Reading: this file has {len(receivers)} distinct strong-receiver "
                  f"clusters. Lanza/Marinescu's interpretation is that such a file "
                  f"is doing the work of multiple cohesive units; splitting along "
                  f"the receiver boundaries is the canonical Extract Class move._")
        elif len(receivers) == 1:
            print(f"_Reading: one strong-receiver cluster (`{receivers[0]}`) plus other "
                  f"smaller clusters. The single strong cluster is the primary "
                  f"extraction candidate._")
        else:
            print("_Reading: multiple clusters but none classified strong. "
                  "File may be a god-module without a clean class hiding inside._")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
