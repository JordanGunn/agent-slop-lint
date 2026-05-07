# Composition detection methods

This directory documents the detection methods that the
`composition.*` rule suite (and adjacent rules in `structural.*`
and `lexical.*`) draws from. Each method is documented with its
problem statement, signal purpose, algorithm sketch, citations,
the modifications we made from the published version, and an
ELI5 section.

The methods are not competitors. They form a measurement battery —
each illuminates a different facet of the same cluster — and a
production rule combines two or more profile signals to make a
specific review-action recommendation. See
[`docs/observations/composition/03.md`](../../observations/composition/03.md)
for the cross-method evaluation that motivates this layout.

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

## Method-to-rule mapping

The methods feed multiple rules. The mapping is many-to-many: a
single method usually contributes to several rules, and a single
rule usually consumes several methods. Approximate current
allocation:

| Rule | Primary methods |
|---|---|
| `composition.first_parameter_drift` | multi-criteria + body-shape + within-cluster affix |
| `composition.affix_polymorphism` | closed-alphabet entity (existing kernel; v2.3 is the planned successor) |
| `composition.implicit_type` (proposed) | closed-alphabet entity |
| `structural.extract_class` (proposed) | Lanza/Marinescu detection |
| `lexical.inconsistent_naming` (proposed) | within-cluster affix (low coverage on real cluster) + dominant text |

Latent topic modeling is currently retained for orientation
research; it has not been promoted to a rule.

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
