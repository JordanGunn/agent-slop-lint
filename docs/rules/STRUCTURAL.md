---
status: locked
stability: requires_migration
ship_state: Completed, but requires migration under sub-category if lexical and semantic rules are approved.
updated: 2026-04-24
---


# Structural Rules

Structural rules measure the shape of code: control flow, dependency graphs, class hierarchies, and change history. They operate on deterministic tree traversals and graph algorithms over source and git history. No models, no embeddings, no external corpora.

This is the category every slop rule belongs to today. All rules listed here are production-ready, have published empirical grounding in their cited sources, and ship enabled by default unless noted otherwise.

See `TAXONOMY.md` for the category system this document fits into. See `LEXICAL.md` and `SEMANTIC.md` for the two adjacent categories.

## Category properties

Measurement substrate: AST, import graph, inheritance graph, commit history, file size.

Compute profile: fast. Every rule in this category runs in seconds on repositories of tens of thousands of files. No network, no external models, no precomputed artifacts.

Determinism: full. Identical source and identical git history produce identical output.

Failure modes: parser edge cases, threshold miscalibration against a language idiom (documented per rule), shallow clones breaking history-dependent rules.

Interpretation burden: low. Every violation can be explained in one or two sentences to anyone familiar with standard software-engineering literature.

## Rule inventory

Twelve rules across seven subcategories. Every rule's default threshold and divergence from canonical sources is documented in the rule reference, which lives in the existing `CONFIG.md` and is being ported to this document as part of the taxonomy migration.

| Rule (fully qualified) | Subcategory | Default | Citation |
|---|---|---|---|
| `structural.complexity.cyclomatic` | complexity | CCX > 10 | McCabe 1976 |
| `structural.complexity.cognitive` | complexity | CogC > 15 | Campbell 2018 |
| `structural.complexity.weighted` | complexity | WMC > 40 | Chidamber & Kemerer 1994 |
| `structural.halstead.volume` | halstead | V > 1500 | Halstead 1977 |
| `structural.halstead.difficulty` | halstead | D > 30 | Halstead 1977 |
| `structural.npath` | npath | NPath > 400 | Nejmeh 1988 |
| `structural.hotspots` | hotspots | 14d window | Tornhill 2015 |
| `structural.packages` | packages | D' > 0.7 | Martin 1994 |
| `structural.deps` | deps | any cycle | Tarjan 1972 |
| `structural.orphans` | orphans | disabled | — |
| `structural.class.coupling` | class | CBO > 8 | Chidamber & Kemerer 1994 |
| `structural.class.inheritance.depth` | class | DIT > 4 | Chidamber & Kemerer 1994 |
| `structural.class.inheritance.children` | class | NOC > 10 | Chidamber & Kemerer 1994 |

## Subcategories

**complexity** — per-function and per-class complexity measurements. Three rules. Two should never be disabled (cyclomatic, cognitive); if noisy, raise thresholds rather than turning off. The third (weighted) is meaningless in codebases without classes and may be disabled for functional or scripting projects.

**halstead** — information-content metrics based on operator and operand counts. Two rules. Catches cognitive density that cyclomatic and cognitive complexity miss — particularly long functions that touch many symbols without nesting. slop's defaults diverge from canonical Halstead thresholds; see rule reference for rationale.

**npath** — combinatorial path count through a function. One rule. Catches explosion that cyclomatic complexity underreports because CCX is additive and NPath is multiplicative. slop's default (400) is tuned above typical modern CLI dispatch patterns; Nejmeh's original 200 was calibrated on pre-OO C.

**hotspots** — complexity × churn per file, after Tornhill. One rule. slop uses a 14-day default window rather than Tornhill's canonical one-year because agentic-era rot accumulates on a steeper curve and a one-year window drowns recent signal in human-era noise. Disable on shallow clones.

**packages** — Martin's distance-from-main-sequence metric per package. One rule. Supported in every language slop covers, though abstract-type detection is language-specific (Go interfaces, Python ABCs/Protocols, etc.). JavaScript has no native abstract concept, so JS-only projects may see expected noise in this rule; it ships at severity `warning` by default.

**deps** — dependency cycle detection via Tarjan's SCC. One rule. Fails on any cycle by default.

**orphans** — unreferenced-symbol detection. One rule. Advisory only, disabled by default, intended for periodic cleanup audits rather than CI gating. False positive rate is high enough that a permanent gate erodes trust.

**class** — three rules (CBO, DIT, NOC) from the Chidamber-Kemerer suite, plus weighted methods (listed under complexity above). All three can be disabled for non-OOP codebases without affecting other rules.

## Per-rule reference

The full per-rule reference — thresholds explained in practice, when to raise, when to lower, when to disable, divergence notes from canonical sources — currently lives in `CONFIG.md`. Under the new taxonomy it will be ported into per-rule sections of this document. The migration is a documentation rewrite, not a behavior change. No thresholds move, no rule logic changes, no new rules. Only fully-qualified names in examples and config schemas are updated.

Until the port is complete, readers should treat `CONFIG.md` as the authoritative per-rule reference and this document as the authoritative category overview.

## Profiles

The three built-in profiles (`default`, `lax`, `strict`) continue to ship. Under the new taxonomy the TOML keys reflect the full path:

```toml
[rules.structural.complexity]
cyclomatic_threshold = 10
cognitive_threshold = 15
weighted_threshold = 40

[rules.structural.hotspots]
since = "14 days ago"
min_commits = 2
fail_on_quadrant = ["hotspot"]
```

The CLI shorthands (`slop check complexity` resolving to `slop check structural.complexity`) remain. Fully qualified names are canonical in config and JSON output.

## Language support

| Language | Complexity | Hotspots | Packages | Deps | Class |
|---|---|---|---|---|---|
| Python | yes | yes | yes | yes | yes |
| JavaScript | yes | yes | partial* | yes | yes |
| TypeScript | yes | yes | yes | yes | yes |
| Go | yes | yes | yes | yes | yes |
| Rust | yes | yes | partial* | partial | yes |
| Java | yes | yes | yes | yes | yes |
| C# | yes | yes | yes | yes | yes |

*Packages rule degrades where the language lacks a native abstract-type concept distinct from concrete classes.*

Unsupported languages are silently excluded from the relevant rules rather than erroring.

## Relationship to other categories

Structural rules are the floor. Every slop-enabled project should run them. They are cheap, deterministic, and well-understood.

Lexical and semantic rules (see `LEXICAL.md`, `SEMANTIC.md`) are orthogonal axes, not replacements. A file can be structurally clean (low complexity, low coupling, no cycles) and still be lexically degenerate (vocabulary inflation, inconsistent naming) or semantically incoherent (doing three unrelated things whose names happen not to collide). The reverse also holds.

Expect all three categories to run together in mature adoption. Expect structural-only to be the first adoption stage for most projects.

## Migration note

All existing rules have been renamed to the fully-qualified form under `structural.*`. Config files using the old flat names (e.g. `[rules.complexity]` instead of `[rules.structural.complexity]`) will be supported as a deprecation shim for at least two minor versions, emitting a warning suggesting the updated form. No behavior differences between the shim and the canonical form are expected.
