# Lexical detection methods

This directory documents the detection methods that several
`lexical.*` rules draw from. Each method is documented with its
problem statement, signal purpose, algorithm sketch, citations,
the modifications we made from the published version, and an
ELI5 section.

The methods are not competitors. They form a measurement battery —
each illuminates a different facet of the same cluster — and a
production rule combines two or more profile signals to make a
specific review-action recommendation. See
[`docs/observations/composition/03.md`](../../observations/composition/03.md)
for the cross-method evaluation that motivates this layout.

> **Note on directory naming.** This directory was originally
> ``docs/methods/composition/`` because the methods are about
> detecting compositional debt. In v1.2.0 the rules these
> methods feed were collapsed into the ``lexical.*`` suite (per
> slop's substrate-naming convention — see
> [`docs/philosophy/naming-spec.md`](../../philosophy/naming-spec.md)),
> and the directory moved to ``docs/methods/lexical/`` to match.
> The methods themselves are unchanged; the algorithms still
> detect compositional patterns, but the rules they produce live
> under ``lexical.*``.

## Method index

| Method | Question it answers | Page |
|---|---|---|
| Dominant text | What is this cluster *named* like? | [→](dominant_text.md) |
| Body shape signatures | Are these functions doing the same thing? | [→](body_shape_signatures.md) |
| Closed alphabet entity | Is this token set acting as a type? | [→](closed_alphabet_entity.md) |
| Within-cluster affix | Are members named consistently or arbitrarily? | [→](within_cluster_affix.md) |
| Latent topic modeling | What concepts cohabit, regardless of cluster boundaries? | [→](latent_topic_modeling.md) |
| Multi-criteria ranking | Is this individual function a strong cluster member? | [→](multi_criteria_ranking.md) |
| Lanza/Marinescu detection | Is this whole file doing the work of multiple cohesive units? | [→](lanza_marinescu_detection.md) |

## Method-to-rule mapping (v1.2.0)

The methods feed multiple rules. The mapping is many-to-many: a
single method usually contributes to several rules, and a single
rule usually consumes several methods.

| Rule | Primary methods |
|---|---|
| `lexical.imposters` | multi-criteria ranking (body-shape + receiver-call density + modal-token overlap) |
| `lexical.sprawl` | closed-alphabet entity + within-cluster affix |
| `lexical.slackers` | within-cluster affix (LOW coverage on real cluster) |
| `lexical.confusion` | Lanza/Marinescu detection (file-level multi-receiver) |
| `lexical.stutter` | unified hierarchy-aware kernel (own implementation) |

Latent topic modeling and dominant-text labeling are currently
retained for orientation research; they have not been promoted
to rules. The PoC scripts under
``scripts/research/composition_poc_v2/`` remain the canonical
reference for the algorithms.

## Reading these docs

Each method document follows the same structure:

1. **Problem.** What concrete review action would this method help
   identify or rule out?
2. **Signal purpose.** What measurement does this method produce,
   and how should that measurement be read?
3. **Algorithm.** Implementation sketch, in as much detail as needed
   to match the production code without re-deriving the math.
4. **Citations.** Primary sources (papers, books) the method draws
   from.
5. **Modifications.** Where the slop implementation differs from
   the published version, and why.
6. **ELI5.** Plain-language summary for readers who don't want the
   formal version. Aimed at "smart developer who isn't a software-
   engineering researcher."

## What's not here

- Per-rule documentation (what the rule does at runtime, what
  thresholds it uses, how to configure it). That lives under
  [`docs/rules/composition/`](../../rules/composition/) and the
  equivalent for other suites.
- Empirical evaluation (which findings hold up, which don't). That
  lives under [`docs/observations/composition/`](../../observations/composition/).
- Theoretical foundations of the metrics slop is built on. That
  lives in [`docs/philosophy/`](../../philosophy/).

These method docs are the layer between "what is this rule" and
"why does this rule exist" — they say "how does the detection
algorithm actually work and what is its provenance."
