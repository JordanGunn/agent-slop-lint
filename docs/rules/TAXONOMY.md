---
status: future_plan
stability: exploratory
ship_state: planned suite taxonomy; not implemented in the current CLI or config schema
purpose: define the long-term suites, evidence posture, naming principles, and migration direction for slop
updated: 2026-04-28
---

# Rule Taxonomy

> **This document describes a planned taxonomy, not the current public
> interface.** Current released rule names are still the historical names
> (`complexity.*`, `halstead.*`, `npath`, `hotspots`, `packages`, `deps`,
> `orphans`, `class.*`). The taxonomy below is the intended direction for a
> future migration. No behavior, thresholds, config keys, or exit codes change
> until that migration is implemented with compatibility shims.

This document defines the long-term suite system for `slop`. It exists so
future rule work has a stable conceptual home before code is written, and so
experimental surfaces do not inherit the trust posture of the stable structural
suite by accident.

The core boundary is narrow:

`slop` measures properties of the codebase artifact and its local history. It
does not measure agent sessions, human approval, provenance chains, memory
freshness, planning quality, or workflow authority.

## Suites

The planned taxonomy is implemented as suites, not merely as rule-name prefixes.
A suite is a separately runnable rule family with its own evidence posture,
dependency profile, default severity posture, and adoption story.

The current product is effectively the structural suite plus two
Halstead-derived legacy rules. Future suites may share the same kernels and
primitives, but they should not share the same trust surface by default.

Planned CLI shape:

```bash
slop lint                 # run the configured default suite/profile
slop structural           # stable structural suite; today's slop lint migrates here
slop comprehension        # deterministic comprehension proxies; planned
slop lexical              # vocabulary-quality checks; exploratory
slop semantic             # model-backed concept checks; experimental

slop check structural     # explicit check form remains valid
slop rules structural     # list rules for one suite
```

Future rules belong to exactly one top-level suite:

| Suite | Measures | Substrate | Default posture |
|---|---|---|---|
| `structural` | Shape and graph risk | AST, control flow, import graph, inheritance graph, package graph, git churn | default-on when established |
| `comprehension` | Artifact proxies for comprehension burden | operator/operand counts, entropy, readability features, information-density metrics | supported or advisory depending on calibration |
| `lexical` | Vocabulary discipline | identifiers, comments, docstrings, token streams, morphology, project dictionaries | advisory until empirically calibrated |
| `semantic` | Meaning relationships | embeddings, topic models, language-model or code-model representations | opt-in advisory unless strongly validated |

The suites are separated by measurement substrate, not by how serious a
violation feels. A dependency cycle and an inflated naming cluster can both be
harmful, but they fail differently, require different explanations, and deserve
different adoption defaults.

## Suite Definitions

**Structural rules** measure shape: control-flow paths, dependency direction,
cycles, class coupling, inheritance depth, package balance, and churn-weighted
growth. They are deterministic from source code and git history. Their failure
modes are parser gaps, language idioms, and threshold calibration.

**Comprehension rules** measure artifact proxies for cognitive and readability
burden. These rules do not claim to measure cognition directly. They measure
properties of the code that research has treated as proxies for comprehension
cost: information volume, symbolic density, entropy, readability features, and
similar artifact-derived signals. Halstead-derived rules belong here, not under
`structural`, because their concept is information density rather than code
shape.

**Lexical rules** measure vocabulary. They operate on identifier splits,
comments, docstrings, and project-local dictionaries. They detect naming
inflation, inconsistent vocabulary, disposable one-off terms, and vocabulary
overlap that may indicate hidden coupling. They are mostly deterministic, but
their thresholds need domain calibration.

**Semantic rules** measure meaning relationships using learned or computed
representations. They detect concept-level cohesion, synonym clusters beyond
surface-form similarity, and name/implementation mismatch. They depend on
pinned model artifacts or equivalent representations, so they carry the highest
operational and interpretive burden.

## Evidence Posture

Evidence maturity is separate from suite. It controls default severity and
whether a rule is allowed to gate CI by default.

| Evidence posture | Meaning | Allowed default |
|---|---|---|
| `established` | Long-standing metric, deterministic computation, operational precedent, calibrated threshold family | may be enabled by default as `error` |
| `supported` | Research supports the artifact as a comprehension or maintenance proxy, but thresholds or transferability require caution | may be enabled by default as `warning`, or opt-in as `error` |
| `exploratory` | Phenomenon is plausible or literature-backed, but the detector is novel or uncalibrated | disabled by default; warning/report only |
| `experimental` | Requires external models, high calibration burden, or uncertain transferability | disabled by default; advisory only |

Suite does not directly determine exit behavior. A `structural` rule can be
advisory, as `orphans` is today. A future `lexical` rule could eventually gate
CI only after evidence and calibration justify that posture. Until then,
novel rules remain opt-in warnings or report-only signals.

## Shared Kernel Substrate

The suite boundary is a product and trust boundary, not a hard implementation
boundary. Suites may share deterministic kernels:

- tree-sitter parsing
- `fd` file discovery
- `rg` text search
- git history inspection
- identifier splitting
- import graph construction
- AST traversal
- output and receipt models

Sharing kernels is desirable. Sharing default severity, install burden, or
claims of maturity is not. A lexical rule can reuse tree-sitter and `rg`
without becoming part of the stable structural suite. A semantic rule can reuse
identifier extraction without inheriting structural's CI-gate posture.

## Naming Principle

Canonical rule names should describe the user-facing maintainability concern,
not necessarily the academic formula.

The source metric still matters. It belongs in documentation, citations,
violation help text, and implementation notes. But users should not need to know
the original author's name to understand what the rule is warning about.

Examples:

| Academic source | Legacy name | Preferred canonical direction |
|---|---|---|
| McCabe cyclomatic complexity | `complexity.cyclomatic` | `structural.complexity.cyclomatic` |
| Campbell cognitive complexity | `complexity.cognitive` | `structural.complexity.cognitive` |
| Nejmeh NPath | `npath` | `structural.complexity.npath` |
| Halstead Volume | `halstead.volume` | `comprehension.information_volume` |
| Halstead Difficulty | `halstead.difficulty` | `comprehension.symbol_difficulty` |

The Halstead examples are the important precedent: the future rule name should
describe dense information content and symbolic difficulty, while the docs cite
Halstead as the root source.

## Planned Migration

The migration is conceptual first and behavioral later. No current name should
be removed until compatibility aliases exist and have been carried for at least
two minor versions.

| Current name | Planned canonical name | Notes |
|---|---|---|
| `complexity.cyclomatic` | `structural.complexity.cyclomatic` | shape/control-flow metric |
| `complexity.cognitive` | `structural.complexity.cognitive` | control-flow readability metric; despite the name, substrate is structural |
| `complexity.weighted` | `structural.class.weighted_methods` | CK WMC; current grouping is historical |
| `npath` | `structural.complexity.npath` | path-count structural metric |
| `hotspots` | `structural.hotspots` | churn x complexity over local git history |
| `packages` | `structural.packages` | package graph balance |
| `deps` | `structural.deps` | import/dependency cycles |
| `orphans` | `structural.orphans` | reachability/reference graph; advisory by default |
| `class.coupling` | `structural.class.coupling` | CK CBO |
| `class.inheritance.depth` | `structural.class.inheritance_depth` | CK DIT |
| `class.inheritance.children` | `structural.class.inheritance_children` | CK NOC |
| `halstead.volume` | `comprehension.information_volume` | based on Halstead Volume |
| `halstead.difficulty` | `comprehension.symbol_difficulty` | based on Halstead Difficulty |

CLI conveniences may remain shorter than canonical names. For example,
`slop check complexity` can continue to mean the structural complexity family.
The canonical names should be used in JSON output, generated config, and rule
documentation once the migration lands. `slop structural` should be treated as
the stable suite entrypoint rather than only as a filter over a larger rule bag.

## Config Surface

The future config schema adds one suite layer and moves comprehension rules
out of the structural namespace:

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

[rules.comprehension.information_volume]
threshold = 1500
severity = "error"

[rules.comprehension.symbol_difficulty]
threshold = 30
severity = "error"

[suites]
default = ["structural"]

[rules.lexical]
enabled = false

[rules.semantic]
enabled = false
```

Exact key names are not stable until implementation. The principle is stable:
Halstead-derived rules become comprehension proxies, not structural rules. The
default suite remains `structural` unless a profile explicitly opts into other
suites.

## Graduation Policy

Future candidate rules graduate only after they meet explicit criteria:

1. The measured artifact property is defined precisely.
2. The computation is deterministic, or any required model artifact is pinned.
3. The detector is evaluated against a reference corpus.
4. The false-positive rate matches the proposed default severity.
5. The violation can be explained in one actionable sentence.
6. The rule's default behavior matches its evidence posture.

Exploratory and experimental rules should not produce exit code `1` by default.
They may emit warnings, reports, or JSON-only findings while calibration is in
progress.

## Boundary With Other Tools

`slop` should not grow into a provenance ledger, memory system, policy engine,
or agent governance platform. Those tools may be valuable, but they answer a
different question.

In scope:

- source tokens
- identifiers, comments, and docstrings
- AST shape
- import and dependency graphs
- class and package graphs
- git-local churn
- deterministic run receipts for `slop` output
- pinned artifact proxies for comprehension or semantic analysis

Out of scope:

- agent-session provenance
- human approval chains
- memory freshness
- planning-state ledgers
- runtime attestation
- security sandbox policy
- explanations of why an agent chose an implementation

## Downstream Documents

This taxonomy is the parent document for suite-specific plans:

- `STRUCTURAL.md` covers the stable shape and graph suite.
- `COMPREHENSION.md` covers the planned information-density and readability suite.
- `LEXICAL.md` covers the exploratory vocabulary-quality suite.
- `SEMANTIC.md` covers the experimental model-backed concept-quality suite.

The philosophy document `docs/philosophy/artifact-proxies.md` is the natural
home for the broader scientific rationale: cognitive-load measurement,
program-comprehension studies, readability models, and why artifact proxies are
useful without pretending to measure cognition directly.
