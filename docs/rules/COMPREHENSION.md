---
status: future_plan
stability: exploratory
ship_state: planned suite; current Halstead-derived rules still ship under legacy names
purpose: define the comprehension suite for artifact-derived proxies of readability and cognitive burden
updated: 2026-04-28
---

# Comprehension Rules

> **This document describes a planned suite.** The current released CLI still
> exposes Halstead-derived rules as `halstead.volume` and
> `halstead.difficulty`. This document records the intended long-term home and
> naming direction for those rules and for future readability or
> information-density metrics.

Comprehension rules measure artifact-derived proxies for how much effort code
demands from a human or agent trying to understand it. They do not measure
cognition directly. They measure source-code properties that research has used
as proxies for comprehension burden.

This suite exists because not every useful metric is structural. A function
can have low branch complexity and no dependency problem while still being dense
with operators, operands, symbols, and local vocabulary. That density matters to
maintenance, but it is not code shape in the same sense as cyclomatic
complexity, dependency cycles, or class coupling.

See `TAXONOMY.md` for the suite system this document fits into.

The planned command surface is `slop comprehension`. It should remain separate
from `slop structural` even though both suites can share tokenization,
tree-sitter, and output kernels.

## Suite Properties

Measurement substrate: source tokens, operators, operands, identifier tokens,
line counts, entropy, indentation, comment density, and other readability
features derivable from the codebase artifact.

Compute profile: cheap to moderate. Most rules should run in seconds and should
not need network access, project-specific training, or external model downloads.

Determinism: high. Rules in this suite should be deterministic from source
content and config. If a future readability model is used, it must be pinned and
versioned before the rule can graduate.

Failure modes: threshold transferability, language-specific syntax effects,
generated code, data-heavy files, and functions that are intentionally dense
because they implement compact mathematical or parsing logic.

Interpretation burden: medium. A structural violation often explains itself
with a graph or count. A comprehension violation needs a short explanation of
what artifact proxy is being measured and why it is associated with readability
or cognitive burden.

## Why Halstead Belongs Here

Halstead metrics are computed from source code, but their claim is not primarily
about structure. They count operators and operands to estimate information
content, difficulty, and effort. That places them closer to readability and
comprehension burden than to structural shape.

The current rule names are historically accurate:

- `halstead.volume`
- `halstead.difficulty`

The future user-facing names should describe the concern:

- `comprehension.information_volume` — based on Halstead Volume
- `comprehension.symbol_difficulty` — based on Halstead Difficulty

The citations remain load-bearing. The suite and names simply make the user
surface clearer: these rules flag dense symbolic/information load, not generic
"Halsteadness."

## Rule Inventory

### `comprehension.information_volume`

Current legacy rule: `halstead.volume`

Source metric: Halstead Volume, `V = N * log2(n)`, where `N` is program length
and `n` is vocabulary size.

User-facing meaning: the function contains a high amount of symbolic
information. This can make a function difficult to scan even when it has few
branches.

Default migration target: preserve the existing threshold initially
(`V > 1500`) and carry the current behavior through a compatibility alias.

Evidence posture: `supported`. Halstead's specific effort formulas should not
be overclaimed, but operator/operand volume remains a useful artifact proxy and
has appeared in later readability and program-comprehension work.

### `comprehension.symbol_difficulty`

Current legacy rule: `halstead.difficulty`

Source metric: Halstead Difficulty,
`D = (unique_operators / 2) * (total_operands / unique_operands)`.

User-facing meaning: the function's operator/operand balance suggests dense
symbolic manipulation. This catches functions that are not branchy but still
force a reader to track many relationships.

Default migration target: preserve the existing threshold initially (`D > 30`)
and carry the current behavior through a compatibility alias.

Evidence posture: `supported`. Treat as an artifact proxy rather than a direct
measure of mental effort.

## Candidate Future Rules

Every rule below is a candidate. None currently ship.

### `comprehension.readability_entropy`

Use a small feature set inspired by simpler readability models: lines of code,
Halstead Volume, token entropy, and possibly identifier length. The goal is not
to reproduce a full learned readability model, but to test whether a compact,
deterministic feature set produces actionable outliers.

Relevant literature: Buse and Weimer's readability model; Posnett, Hindle, and
Devanbu's simpler readability model.

Risk: a composite score can become opaque. This rule should not ship unless its
violation text can name the dominant contributing features.

### `comprehension.local_entropy`

Measure token or identifier entropy within a function or file. High entropy may
indicate broad vocabulary or symbolic spread; low entropy may indicate
repetition. This is a candidate only if empirical probes show it adds signal
beyond existing Halstead-derived metrics.

Risk: entropy is easy to compute and easy to overinterpret.

### `comprehension.readability_features`

Report-only feature extraction for readability research: line length,
indentation depth, comment density, identifier length, token entropy, and
information volume. This may be useful before any composite readability rule is
promoted.

Risk: feature reports are useful for investigation but too noisy for CI gating
without a calibrated decision rule.

## Relationship To Other Suites

Comprehension rules are not replacements for structural rules. A function can be
structurally simple but information-dense, or structurally complex but lexically
clear. The suites should run together only when configured to do so.

Comprehension rules are also distinct from lexical rules. A lexical rule cares
about vocabulary quality and naming consistency. A comprehension rule cares
about artifact-level reading burden, even when every name is domain-appropriate.

Semantic rules sit above comprehension rules in dependency and interpretation
burden. A semantic rule may need embeddings to judge whether a name matches an
implementation. A comprehension rule should remain computable from local source
features whenever possible.

## Evidence And Default Severity

Existing Halstead-derived rules already ship and may retain their current
severity during the migration, but their documentation should become more
careful: they are supported artifact proxies, not direct cognitive-load
measurements.

Future comprehension rules should start as warnings or report-only findings
unless empirical calibration justifies stronger behavior.

Graduation criteria:

1. The measured feature is defined precisely.
2. The detector is deterministic from source and config.
3. The metric separates known-clean and known-problematic reference corpora.
4. The false-positive rate supports the proposed severity.
5. The violation explains the artifact property in one actionable sentence.

## Configuration Surface

Provisional future config:

```toml
[rules.comprehension.information_volume]
enabled = true
threshold = 1500
severity = "error"

[rules.comprehension.symbol_difficulty]
enabled = true
threshold = 30
severity = "error"

[rules.comprehension.readability_entropy]
enabled = false
severity = "warning"
```

The exact key names and thresholds are placeholders until the namespace
migration is implemented.

## Open Questions

- Should Halstead-derived rules keep `error` severity after the rename, or move
  to warning in conservative profiles?
- Should comprehension include only deterministic formula metrics, or can a
  pinned learned readability model live here?
- How should slop explain composite readability findings without producing a
  black-box score?
- Should comprehension rules have project-relative thresholds, absolute
  thresholds, or both?

## Sources To Track

- Halstead, Maurice H. *Elements of Software Science*. 1977.
- Buse, Raymond P. L., and Westley R. Weimer. "Learning a Metric for Code
  Readability." IEEE Transactions on Software Engineering, 2010.
- Posnett, Daryl, Abram Hindle, and Premkumar Devanbu. "A Simpler Model of
  Software Readability." 2011.
- Scalabrino, Simone, et al. "A Comprehensive Model for Code Readability."
  Journal of Software: Evolution and Process, 2018.
- Fakhoury, Sarah, et al. "The Effect of Poor Source Code Lexicon and
  Readability on Developers' Cognitive Load." ICPC, 2018.
- Peitek, Norman, et al. "Program Comprehension and Code Complexity Metrics:
  An fMRI Study." ICSE, 2021.
