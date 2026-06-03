# Lanza/Marinescu detection strategy

**Status:** Active in v2 PoC battery; **strongest single probe** for
file-level Extract Class candidates.
**PoC:** [`scripts/research/composition_poc_v2/poc7_lanza_marinescu.py`](../../../scripts/research/composition_poc_v2/poc7_lanza_marinescu.py)

## Problem

Per-cluster analysis tells you about a single group of related
functions. It doesn't see that an entire FILE has multiple distinct
groups of related functions cohabiting — and that each group is
self-coherent, but the file as a whole is doing the work of
several cohesive units.

The textbook example, from slop's `output.py`:

- 5 functions taking `result: LintResult` (the renderer family)
- 5 functions taking `rule_pairs: list[tuple[str, RuleResult]]`
  (the category-view family)
- 4 functions taking `rule_name: str` (the label-helper family)

Each is a coherent cluster. The file holds three of them. The
review action isn't "extract a class for these methods" (we have
three families, no single class covers them); it's **"split this
file into modules along the receiver boundaries."**

This is the canonical Extract Class scenario in
Lanza & Marinescu's terminology, and the file-level signal is
exactly what their detection-strategy framework was designed to
catch.

## Signal purpose

For each Python file in the corpus, the rule produces a boolean
**Extract Class candidate** verdict by composing three thresholds:

1. **function_count** — total number of functions in the file
2. **cluster_count** — number of distinct first-parameter clusters
   in the file with size ≥ minimum cluster threshold
3. **strong_receivers** — clusters whose first-parameter passes the
   `_classify_cluster` strong/weak/false-positive verdict as
   "strong"

The detection rule:

```
ExtractClassCandidate(file) =
    (function_count >= MIN_FUNCTIONS_PER_MODULE)
    AND (cluster_count >= MIN_CLUSTERS_PER_MODULE)
    AND (each cluster size >= MIN_CLUSTER_SIZE)
```

Default thresholds (calibration starting point):
- MIN_FUNCTIONS_PER_MODULE = 5
- MIN_CLUSTERS_PER_MODULE = 2
- MIN_CLUSTER_SIZE = 3

Reading the output:

| Signal | Reading |
|---|---|
| 0 candidates flagged | Files are coherent at single-receiver granularity. No file-level Extract Class refactor needed. |
| 1-N candidates flagged with 1 strong receiver | One strong cluster + smaller clusters. The strong cluster is the primary extraction candidate; smaller clusters may be helpers around it. |
| 1-N candidates flagged with multiple strong receivers | Multiple distinct cohesive units in one file. Split along receiver boundaries. |

The "multiple strong receivers in one file" case is the strongest
signal. It is the textbook Lanza/Marinescu trigger.

## Algorithm

```
for each Python file F:
    functions_in_F = enumerate_functions(F)
    if len(functions_in_F) < MIN_FUNCTIONS_PER_MODULE:
        continue

    by_param = group_by(extract_first_param, functions_in_F)
    by_param.discard(self, cls)
    clusters = {p: members for p, members in by_param.items()
                if len(members) >= MIN_CLUSTER_SIZE
                   and len(p) >= 2}

    if len(clusters) < MIN_CLUSTERS_PER_MODULE:
        continue

    strong_receivers = [p for p, members in clusters.items()
                        if classify_cluster(p, types_of(members)) == "strong"]

    flag(F, function_count=len(functions_in_F),
         cluster_count=len(clusters),
         strong_receivers=strong_receivers)
```

Composes existing slop primitives (`enumerate_functions`,
`_extract_first_param`, `_classify_cluster`). No new detection
mathematics — only threshold composition.

## Citations

- **Lanza, M. & Marinescu, R. (2006).** *Object-Oriented Metrics in
  Practice: Using Software Metrics to Characterize, Evaluate, and
  Improve the Design of Object-Oriented Systems.* Springer.
  The canonical book for metric-based code-smell detection. Their
  framework — "detection strategies" — explicitly composes multiple
  metrics with calibrated thresholds into rules for specific
  smells. Chapter 5 covers Extract Class via WMC + cohesion +
  attribute-access patterns. This method is the same idea adapted
  to slop's substrate (free-function modules) instead of OO
  classes.

- **Marinescu, R. (2004).** "Detection Strategies: Metrics-Based
  Rules for Detecting Design Flaws." *Proceedings of the 20th IEEE
  International Conference on Software Maintenance*, 350-359.
  The academic-paper precursor to the book. Establishes the
  methodology: take multiple metrics, calibrate thresholds, AND
  them together, get a detection strategy.

## Modifications

- **Substrate.** Lanza/Marinescu work on classes (WMC, TCC, CBO,
  ATFD). slop's primary substrate is free-function modules. We
  translate their class-level detection strategy to module-level:
  function-count instead of WMC, cluster-count instead of cohesion-
  break, first-parameter clustering instead of attribute access.
  The framework is unchanged; only the input units differ.
- **Cohesion via clustering, not TCC/LCOM.** Lanza/Marinescu's
  cohesion metrics (Tight Class Cohesion, Lack of Cohesion of
  Methods) require attribute-access analysis on classes. We use
  the *count of distinct first-parameter clusters* as a cohesion
  proxy: if a module has 3 distinct receivers, it has 3 distinct
  cohesive units. This is a coarser signal than TCC but works for
  the file-split decision.
- **Thresholds are starting points.** Lanza/Marinescu emphasize
  empirical calibration of thresholds for each metric. Our
  numbers (5 / 2 / 3) are first-pass values that produce sensible
  output on slop. Cross-corpus calibration is required before
  shipping.
- **Reuses `_classify_cluster` for receiver verdicts.** The
  underlying `_classify_cluster` function classifies first-param
  clusters as strong / weak / false-positive based on parameter
  semantics. This is a slop-specific extension; Lanza/Marinescu
  don't have an exact equivalent.

## ELI5

Look at a single file. Don't worry about whether it's beautiful or
ugly; just count things.

1. **How many functions are in this file?** If it's only two or
   three, this analysis doesn't apply — too small to extract
   anything from.

2. **How many distinct receivers do those functions cluster
   around?** Group functions by their first parameter. If
   everything takes a different first parameter, you have no
   cluster. If everything takes the same first parameter, you have
   one cluster — and the file is coherent. If functions split into
   2 or 3 cohesive groups based on their first parameter, the file
   is doing 2 or 3 things.

3. **Are those clusters real receiver groups?** A cluster of 3
   functions all taking `tmp_path: Path` is probably a pytest
   fixture pattern, not a missing class. We classify each cluster
   as strong (real receiver), weak (infrastructure), or false-
   positive (third-party type wrapper). Only strong clusters
   count.

If a file has many functions AND multiple strong-receiver clusters,
that file is doing the work of multiple cohesive units. The
canonical refactor: split it. Each strong-receiver cluster becomes
its own file (or its own class), the helpers travel with their
cluster, and the original file disappears or shrinks to an import
manifest.

The classic example: slop's own `output.py`. 17 functions, three
distinct strong receivers (`result`, `rule_pairs`, `rule_name`).
Split it into `output/result_render.py`, `output/category_view.py`,
`output/rule_label.py` and the file's job becomes obvious.

This rule is conservative by design — it only flags files where
the multi-receiver pattern is clear. It misses files where one
cluster dominates and a few stragglers exist (those are caught by
single-cluster rules). What it catches is cleanly actionable:
"This file is hiding multiple modules. Split."

The conservatism is deliberate. Lanza & Marinescu emphasize that
detection strategies should err toward false-negative over false-
positive: a missed bad smell can be caught later, but a false
recommendation costs the developer trust in the tool. The
file-multi-receiver rule is among the strongest precision signals
slop can produce because the conjunction of three thresholds
filters most incidental cases.
