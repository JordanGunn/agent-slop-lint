---
status: future_plan
stability: requires_migration
ship_state: stable suite direction; current CLI still uses historical flat names
updated: 2026-04-28
---


# Structural Rules

Structural rules measure the shape of code: control flow, dependency graphs, class hierarchies, package graphs, and change history. They operate on deterministic tree traversals and graph algorithms over source and git history. No models, no embeddings, no external corpora.

This is the stable suite for slop rules whose primary signal is structural shape. Most current slop rules belong here, but Halstead-derived rules are better described as comprehension proxies and are planned to move under `comprehension.*` rather than `structural.*`.

Long term, today's `slop lint` behavior should become the configured default profile, while `slop structural` provides an explicit entrypoint for the stable structural suite.

See `TAXONOMY.md` for the category system this document fits into. See `COMPREHENSION.md`, `LEXICAL.md`, and `SEMANTIC.md` for adjacent planned categories.

## Category properties

Measurement substrate: AST, import graph, inheritance graph, commit history, file size.

Compute profile: fast. Every rule in this category runs in seconds on repositories of tens of thousands of files. No network, no external models, no precomputed artifacts.

Determinism: full. Identical source and identical git history produce identical output.

Failure modes: parser edge cases, threshold miscalibration against a language idiom (documented per rule), shallow clones breaking history-dependent rules.

Interpretation burden: low. Every violation can be explained in one or two sentences to anyone familiar with standard software-engineering literature.

## Rule inventory

Eleven current rules belong under the planned structural taxonomy. Every rule's default threshold and divergence from canonical sources is documented in the rule reference, which lives in the existing `CONFIG.md` and is being ported to this document as part of the taxonomy migration.

| Rule (fully qualified) | Subcategory | Default | Citation |
|---|---|---|---|
| `structural.complexity.cyclomatic` | complexity | CCX > 10 | McCabe 1976 |
| `structural.complexity.cognitive` | complexity | CogC > 15 | Campbell 2018 |
| `structural.class.weighted_methods` | class | WMC > 40 | Chidamber & Kemerer 1994 |
| `structural.complexity.npath` | complexity | NPath > 400 | Nejmeh 1988 |
| `structural.hotspots` | hotspots | 14d window | Tornhill 2015 |
| `structural.packages` | packages | D' > 0.7 | Martin 1994 |
| `structural.deps` | deps | any cycle | Tarjan 1972 |
| `structural.orphans` | orphans | disabled | — |
| `structural.class.coupling` | class | CBO > 8 | Chidamber & Kemerer 1994 |
| `structural.class.inheritance.depth` | class | DIT > 4 | Chidamber & Kemerer 1994 |
| `structural.class.inheritance.children` | class | NOC > 10 | Chidamber & Kemerer 1994 |

## Subcategories

**complexity** — per-function control-flow measurements. Cyclomatic and cognitive complexity should rarely be disabled; if noisy, raise thresholds rather than turning off. NPath also belongs here because it measures combinatorial execution paths through a function.

**class** — four rules from the Chidamber-Kemerer family and related class-level structure: weighted methods, CBO, DIT, and NOC. All can be disabled for non-OOP codebases without affecting other rules.

**hotspots** — complexity × churn per file, after Tornhill. One rule. slop uses a 14-day default window rather than Tornhill's canonical one-year because agentic-era rot accumulates on a steeper curve and a one-year window drowns recent signal in human-era noise. Disable on shallow clones.

**packages** — Martin's distance-from-main-sequence metric per package. One rule. Supported in every language slop covers, though abstract-type detection is language-specific (Go interfaces, Python ABCs/Protocols, etc.). JavaScript has no native abstract concept, so JS-only projects may see expected noise in this rule; it ships at severity `warning` by default.

**deps** — dependency cycle detection via Tarjan's SCC. One rule. Fails on any cycle by default.

**orphans** — unreferenced-symbol detection. One rule. Advisory only, disabled by default, intended for periodic cleanup audits rather than CI gating. False positive rate is high enough that a permanent gate erodes trust.

## Per-rule reference

The full per-rule reference — thresholds explained in practice, when to raise, when to lower, when to disable, divergence notes from canonical sources — currently lives in `CONFIG.md`. Under the new taxonomy it will be ported into per-rule sections of this document. The migration is a documentation rewrite, not a behavior change. No thresholds move, no rule logic changes, no new rules. Only fully-qualified names in examples and config schemas are updated.

Until the port is complete, readers should treat `CONFIG.md` as the authoritative per-rule reference and this document as the authoritative category overview.

## Profiles

The three built-in profiles (`default`, `lax`, `strict`) continue to ship. Under the new taxonomy the TOML keys reflect the full path:

```toml
[rules.structural.complexity]
cyclomatic_threshold = 10
cognitive_threshold = 15
npath_threshold = 400

[rules.structural.class]
weighted_methods_threshold = 40
coupling_threshold = 8
inheritance_depth_threshold = 4
inheritance_children_threshold = 10

[rules.structural.hotspots]
since = "14 days ago"
min_commits = 2
fail_on_quadrant = ["hotspot"]
```

The CLI shorthands (`slop check complexity` resolving to `slop check structural.complexity`) remain. Fully qualified names are canonical in config and JSON output. `slop structural` is the planned direct suite command.

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

Structural rules are the floor. Every slop-enabled project should run this suite. It is cheap, deterministic, and well-understood.

Comprehension, lexical, and semantic rules (see `COMPREHENSION.md`, `LEXICAL.md`, `SEMANTIC.md`) are orthogonal axes, not replacements. A file can be structurally clean (low complexity, low coupling, no cycles) and still be information-dense, lexically degenerate, or semantically incoherent. The reverse also holds.

Expect structural and comprehension rules to be the first adoption stage for most projects because slop already ships the underlying legacy metrics. Lexical and semantic rules should remain advisory until their detectors are calibrated.

## Migration note

The planned migration is documentation-only until implemented in code. Config files using the old flat names (for example `[rules.complexity]`) must continue to work until deprecation shims exist and have been supported for at least two minor versions. Halstead-derived rules are intentionally excluded from this structural migration and are documented in `COMPREHENSION.md`.
