---
status: future_plan
stability: exploratory
ship_state: philosophy and evidence model; not a shipped rule contract
purpose: preserve the scientific rationale for artifact-derived proxies without expanding slop beyond codebase measurement
updated: 2026-04-28
---

# Artifact Proxies

`slop` measures codebase artifacts. It does not measure developer cognition,
agent cognition, human approval, or session provenance directly.

The working thesis is narrower and more defensible:

> Some measurable properties of source code and local history act as useful
> proxies for maintainability risk, comprehension burden, and agentic drift.

This document preserves the scientific rationale behind that thesis. It is not
a rule contract. Candidate rules still need formal definitions, empirical
probes, calibration, and severity decisions before they can ship.

## Boundary

In scope for `slop`:

- source-code tokens
- identifiers, comments, and docstrings
- AST shape
- control-flow paths
- import and dependency graphs
- class and package graphs
- local git history
- deterministic run metadata for a `slop` report
- pinned artifact models only when a rule explicitly opts into them

Out of scope for `slop`:

- agent-session provenance
- memory freshness
- human approval chains
- planning ledgers
- runtime attestation
- sandbox or security policy
- explanations of why an agent chose a patch

The out-of-scope items may deserve their own tools. They do not belong in a
codebase artifact linter.

## Evidence Posture

`slop` should distinguish between mature metrics and exploratory proxies.

| Posture | Meaning | Product implication |
|---|---|---|
| `established` | Long-standing metric, deterministic computation, operational precedent | may gate by default |
| `supported` | Research supports the artifact as a proxy, but thresholds require care | warning or calibrated gate |
| `exploratory` | Plausible or literature-backed phenomenon, novel detector | disabled by default; advisory |
| `experimental` | Model-backed, high calibration burden, or uncertain transferability | opt-in advisory only |

The posture should be visible in rule docs and eventually in rule metadata.

## Current Artifact Families

### Structural Shape

Structural metrics measure shape: paths, branches, dependency graphs, class
graphs, package balance, and churn. These are slop's strongest current signals
because they are deterministic, cheap, and grounded in established software
engineering literature.

Examples:

- Cyclomatic Complexity
- Cognitive Complexity
- NPath
- CK class metrics
- dependency cycles
- package distance from the main sequence
- churn-weighted hotspots

### Information Density

Information-density metrics measure how much symbolic content a reader must
track. Halstead-derived metrics are the current example. They are computed from
operators and operands, but their meaning is closer to comprehension burden than
structural shape.

Taxonomy home:

- `information.volume`
- `information.difficulty`

Legacy names:

- `information.volume` (formerly `halstead.volume`)
- `information.difficulty` (formerly `halstead.difficulty`)

## Exploratory Artifact Families

### Readability Models

Readability work treats code comprehension as something partly predictable from
source features: line length, identifier length, indentation, comment density,
Halstead Volume, entropy, and related measurements.

These models are useful to `slop` only if they can be reduced to deterministic,
explainable artifact signals. A black-box readability score is a poor fit unless
its dominant features can be surfaced in the violation.

Sources to track:

- Buse and Weimer, "Learning a Metric for Code Readability", 2010.
- Posnett, Hindle, and Devanbu, "A Simpler Model of Software Readability", 2011.
- Scalabrino et al., "A Comprehensive Model for Code Readability", 2018.

### Lexical Quality

Lexical quality measures vocabulary: naming consistency, generic role nouns,
identifier frequency, and project-local terminology. This is the most natural
next suite after structural and information rules because many detectors can
remain deterministic and cheap.

Candidate subjects:

- generic role or nominalization density
- hapax ratio
- vocabulary growth deviation
- cross-module vocabulary overlap
- naming consistency
- part-of-speech convention violations

Sources to track:

- Abebe et al. on lexical smells.
- Arnaoudova et al. on linguistic antipatterns.
- Lawrie, Feild, and Binkley on identifier naming quality.
- Deissenboeck and Pizka on concise and consistent naming.
- Allamanis et al. on NATURALIZE and code naturalness.

### Semantic And Conceptual Quality

Semantic rules use learned or computed representations to detect relationships
that surface-form tokens miss: identifier cohesion, synonym clusters, conceptual
coupling, and name/implementation mismatch.

These are promising but should be opt-in and advisory until model strategy,
licensing, determinism, and calibration are resolved.

Sources to track:

- Hindle, Barr, Gabel, Su, and Devanbu on naturalness.
- Allamanis, Barr, Devanbu, and Sutton's big-code survey.
- Wainakh, Rauf, and Pradel's IdBench.
- Alon et al. on code2vec.

## Cognitive Load Evidence

Cognitive Load Theory and program-comprehension studies do not turn directly
into lint rules. They provide evidence that some artifact properties have real
human comprehension costs.

Useful measurement families:

- subjective load instruments: Paas scale, NASA-TLX, Leppink et al.
- performance measures: dual-task methodology
- physiological measures: fNIRS, fMRI, eye tracking, pupillometry, HRV

The most relevant bridge for `slop` is artifact-level work showing that poor
lexicon, readability, and complexity correlate with comprehension difficulty or
measured cognitive load.

Sources to track:

- Fakhoury et al., "The Effect of Poor Source Code Lexicon and Readability on
  Developers' Cognitive Load", 2018.
- Peitek et al., "Simultaneous Measurement of Program Comprehension with fMRI
  and Eye Tracking", 2018.
- Peitek et al., "Program Comprehension and Code Complexity Metrics: An fMRI
  Study", 2021.

## Graduation Standard

A scientific source does not automatically create a rule. A candidate proxy
must pass through the rule investigation path:

1. Literature pass.
2. Formal metric definition.
3. Prototype against a reference corpus.
4. Calibration and false-positive review.
5. Rule decision: ship, shelve, or defer.

Rules based on exploratory or experimental proxies should not produce exit code
`1` by default. Their purpose is to surface risk while the evidence matures, not
to pretend a novel detector has the same standing as established structural
metrics.

## Why This Matters For Agentic Code

Agentic code can accumulate comprehension debt faster than human review loops
can inspect it. The agent does not feel the cost of inflated vocabulary, dense
symbolic manipulation, or subtle conceptual drift while generating code. The
next human or agent inherits that cost as a harder search, edit, and review
surface.

`slop` should stay focused on the artifact. Its job is to cheaply and repeatedly
surface measurable codebase conditions that make future work harder.
