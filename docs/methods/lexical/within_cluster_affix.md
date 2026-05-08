# Within-cluster affix re-detection

**Status:** Active in v2 PoC battery; promotion to kernel pending.
**PoC:** [`scripts/research/composition_poc_v2/poc4_within_cluster_affix.py`](../../../scripts/research/composition_poc_v2/poc4_within_cluster_affix.py)

## Problem

A first-parameter cluster groups N functions by what they take as
input. The names of those functions can either follow a clear
template (`format_human, format_quiet, format_json`) or be
arbitrary (`_collect_legacy_derivations, _flatten_canonical_tables,
_migrate_split_stutter_table`). Both are real clusters; the
review action differs:

- Structured names → cluster is a recognized family. The varying
  position is the dispatch dimension. Action: extract appropriately
  (class, table, or accept as is) per other signals.
- Unstructured names → cluster is real but the names don't reflect
  it. Action: rename for consistency before any extraction can be
  evaluated, OR accept that the functions don't belong together
  semantically.

This second case is what the user has called out as "huge" — agents
rarely propose renaming siblings to follow a consistent pattern,
and humans rarely flag it on review either, because each function
name reads fine in isolation. The signal is in the cluster, not the
individual name.

## Signal purpose

For a first-parameter cluster, this method runs the affix-pattern
detector on the cluster's *member function names* (not the
codebase). Output: a **coverage percentage** and a list of detected
patterns.

| Coverage | Reading | Implication |
|---|---|---|
| 100% | Every cluster member fits a single template; closed alphabet | Strong dispatch family. Names already correctly express the cluster's structure. |
| 60-90% | Most members fit a template; outliers exist | Family with a few helpers. Inspect outliers — are they part of the family with bad names, or genuinely different? |
| 30-60% | Partial template fit; mixed cluster | Cluster contains a sub-family with structure plus unrelated helpers. Consider splitting the cluster. |
| < 30% | No coherent template | Cluster is real (shared input) but unstructured. Rename for consistency, or reconsider whether the cluster is a real concept. |

The within-cluster scope makes this distinct from the existing
`composition.affix_polymorphism` rule, which detects affix patterns
across the whole codebase. Same algorithm, different question:
"does this cluster's naming itself follow a pattern?"

## Algorithm

```
for each cluster:
    items = [(name, file, line, split_identifier(name))
             for name in cluster.members]
    patterns = build_affix_patterns(items)  # existing kernel function
    meaningful = [p for p in patterns if total_variants(p) >= 2]

    covered = ⋃ {names appearing in any meaningful pattern}
    coverage = |covered| / |cluster.members|
```

`build_affix_patterns` is slop's existing token-edit-distance-1
detector, reused at finer scope. A pattern records its stem
(the constant tokens) and its variants (the alphabet that varies
in the swap position).

## Citations

Same lineage as the codebase-wide affix detection:

- **Caprile, B. & Tonella, P. (2000).** "Restructuring program
  identifiers based on word usage and stop-word filtering."
  Identifier-pattern restructuring at the codebase level. Same
  algorithm we run here, just at narrower scope.

- **Wille, R. (1982).** "Restructuring lattice theory: an approach
  based on hierarchies of concepts."
  Closed-alphabet detection is the FCA primitive Caprile & Tonella
  build on.

- **Slop's existing `composition.affix_polymorphism` rule** uses
  the same primitive at codebase scope. This method reuses that
  kernel.

## Modifications

- **Scope only.** The algorithm is unchanged from the existing
  affix kernel; only the input changes (cluster members vs. whole
  corpus). No mathematical modification.
- **Coverage as the headline metric.** The codebase-wide affix
  detector reports patterns directly. We report coverage —
  the fraction of cluster members fitting *any* pattern — because
  it's a single number per cluster that's easy to threshold and
  reason about.

## ELI5

You have a cluster of five functions that all take `result` as
their first parameter:

```
format_human, format_quiet, format_json, _group_by_category, _format_footer
```

Look at just the names. Squint past the parameter.

Three of them follow a template: `format_X` where X is `human`,
`quiet`, `json`. The other two don't fit the template — they have
different verbs (`group`, `format` but in the middle) and different
shapes.

Coverage is `3 / 5 = 60%`. Reading: the cluster has a clear core
sub-family (the `format_*` formatters) plus two helpers that
support them. The cluster as a whole isn't a clean template — but
neither is it unstructured noise.

Compare with `red, green, yellow, bold, dim`: every name is a
single word, all from the same alphabet. Coverage 100%. Clean
dispatch family.

Compare with `_collect_legacy_derivations,
_flatten_canonical_tables, _migrate_split_stutter_table`:
no two names share more than one token. Coverage 0%. The functions
have a real shared input (`raw_rules`) but their names don't
express any common structure.

What this is asking is straightforward: **do the names tell the
truth about the cluster?** When the cluster is structured but the
names aren't, that's a renaming opportunity that's almost
invisible at the per-function level — each name reads fine on its
own, but as a family they fail to communicate the shared concept.

Agents rarely propose this kind of rename in review, because the
mismatch is only visible when you see the whole cluster at once.
This method makes it visible.
