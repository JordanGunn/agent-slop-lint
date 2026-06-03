# Dominant text

**Status:** Active in v2 PoC battery; promotion to kernel pending.
**PoC:** [`scripts/research/composition_poc_v2/poc1_dominant_text.py`](../../../scripts/research/composition_poc_v2/poc1_dominant_text.py)

## Problem

When a cluster of related functions is detected, the linter needs
to describe the cluster in terms a reviewer or agent can read at a
glance. "Five functions share `result` as first parameter" doesn't
say what KIND of family the cluster is — a strategy table, a
state-machine, a haphazard bag of helpers. Without that
characterization, the cluster is data without a frame.

Dominant text is the simplest probe that produces a frame.

## Signal purpose

For a cluster of N function names, dominant text answers:

- **Modal token:** the most-frequent token across cluster names (the
  shared verb or noun, if any).
- **Shared stem:** tokens present in ≥ 60% of names. If non-empty,
  the cluster has a recognizable verb-position template.
- **Varying alphabet:** tokens that appear exactly once across the
  cluster. If non-empty, those tokens are likely the dimension along
  which cluster members differ.

Reading the output:

| Modal token | Shared stem | Varying alphabet | Read |
|---|---|---|---|
| `format` ×4 | `format` | `human, json, quiet` | structured family with one varying position; clean dispatch shape |
| `red` ×1 | _none_ | `red, green, yellow, bold, dim` | each name IS its alphabet member; no shared verb; tabular dispatch |
| `optional` ×2 | _none_ | `date, number, string, waiver` | weak shared verb; mixed concerns |
| _various_ | _none_ | _none_ | unstructured cluster (likely incidental shared parameter) |

## Algorithm

```
for each cluster:
    tokens_per_name = [split_identifier(n) for n in cluster.names]
    flat = flatten(tokens_per_name)
    freq = Counter(flat)
    n = len(cluster.names)

    modal_token = freq.most_common(1)
    shared_stem = [t for t, c in freq.items() if c / n >= 0.6]
    # Tokens that are hapax (count=1) AND occupy the last position
    # in their name — these are the differentiator the cluster varies on
    varying_alphabet = {ts[-1] for ts in tokens_per_name
                        if ts and freq[ts[-1]] == 1}
```

Token splitting uses slop's existing `split_identifier`, which
handles snake_case + CamelCase + acronym boundaries.

## Citations

- **Caprile, B. & Tonella, P. (2000).** "Restructuring program
  identifiers based on word usage and stop-word filtering."
  *Proceedings of the 8th International Workshop on Program
  Comprehension*, 97-104.
  Establishes the lineage of identifier-token analysis for
  refactoring detection. Caprile & Tonella focus on standardizing
  identifier conventions across a codebase; we use the same
  primitive (token splitting + frequency) to characterize a
  detected cluster.

- **Lawrie, D., Feild, H. & Binkley, D. (2006).** "Quantifying
  Identifier Quality: An Analysis of Trends." *Empirical Software
  Engineering* 12(4), 359-388.
  Quantitative identifier analysis methodology. Background work
  for treating tokens as a measurable feature rather than free-text.

- **Standard term frequency / bag-of-tokens primitives** from
  information retrieval. Not paper-specific; this is undergraduate
  IR material applied to a software-engineering question.

## Modifications

What we changed from the cited methods:

- **Scope.** Caprile & Tonella analyze whole-codebase identifier
  populations; we apply the same primitive at within-cluster scope
  (where the cluster is already detected by another mechanism).
- **No IDF.** Standard TF-IDF assumes many documents; a single
  cluster typically has 3-8 names, which is too few for
  meaningful IDF. We use raw term frequency.
- **Modal-token labeling and shared-stem heuristic** — specifically
  the rule "≥ 60% of names contain this token = shared stem" — is
  ours, not from a published method. It's a presentation choice,
  calibrated empirically against the slop corpus.

## ELI5

Look at the function names in a cluster:

```
format_human, format_quiet, format_json, _group_by_category, _format_footer
```

Ask three questions:

1. **What word is in most of these names?** Here, `format` appears
   in four of five. That's the *modal token* — what this cluster
   is mostly *about*.
2. **What word is in MOST of them, like 60% or more?** Same answer:
   `format`. So `format` is also the *shared stem* — there's a
   verb-position template here.
3. **What word is unique to each one?** `human`, `quiet`, `json` —
   these are all hapaxes, each appearing exactly once. They're the
   *varying alphabet* — the dimension along which cluster members
   differ.

Now you know what kind of cluster this is: it's a `format_*` family
with three formats. That's a structured dispatch, not random
helpers.

Compare with `red, green, yellow, bold, dim`: no shared word at all,
but each name IS the alphabet member. That's a different shape — a
tabular dispatch where the function name = the dispatch key.

Compare with a cluster like `_collect_legacy_derivations,
_flatten_canonical_tables, _migrate_split_stutter_table`: no modal
token, no shared stem, no clean alphabet. That's an unstructured
cluster — just functions that happen to share an input. The names
themselves don't suggest a refactor.

Dominant text doesn't tell you what to DO with the cluster. It
tells you what *shape* the cluster has, in the language of the
names themselves.
