---
status: exploratory
stability: in development
ship_state: planned suite, not shipped
purpose: investigate the applicability and usefulness of lexical rules as a separate slop suite
updated: 2026-04-28
---

# Lexical Rules

> **This document describes a planned suite.** No lexical rules currently ship in slop. Every rule here is a candidate under active investigation. Thresholds, detectors, and empirical grounding will be validated against reference corpora before any rule graduates to production. Expect the rule list, the configuration surface, and the terminology to evolve during the investigation phase. Nothing in this document should be treated as a stable contract.

Lexical rules measure vocabulary. They operate on tokenized identifier streams, docstrings, and comments. They care about the words themselves: whether they are consistent, concise, appropriately named, drawn from a stable project vocabulary.

This suite fills a gap slop does not currently cover. Structural rules (see `STRUCTURAL.md`) measure the shape of code. Comprehension rules (see `COMPREHENSION.md`) measure information-density and readability proxies. Neither says whether `UserPreferenceOrchestrationManager` reads any worse than `UserPreferences`. Lexical rules close that vocabulary gap.

See `TAXONOMY.md` for the suite system this document fits into. The planned command surface is `slop lexical`; it may share tree-sitter, `rg`, and identifier-splitting kernels with other suites without inheriting their default severity posture.

## Why this suite exists

Three converging observations motivate the addition.

First, there is a mature but underdeployed research literature on lexical quality in software. Lexical smells (Abebe et al., WCRE 2009; SCAM 2011), linguistic antipatterns (Arnaoudova et al., CSMR 2013; EMSE 2016), identifier naming quality (Lawrie et al., ICPC 2006; EMSE 2007), and formal models of concise and consistent naming (Deissenboeck & Pizka, Software Quality Journal 2006) all converge on the same claim: vocabulary quality is a measurable, actionable dimension of code quality, largely orthogonal to structural metrics.

Second, this literature has operational precedent. NATURALIZE (Allamanis et al., FSE 2014) demonstrated that learned lexical rules can produce project-specific suggestions that real maintainers accept: 94% suggestion accuracy, 14 of 18 submitted patches accepted across five open-source projects. Research-prototype detectors exist for lexical smells and linguistic antipatterns. None have been operationalized as a general-purpose, language-agnostic, CI-ready linter.

Third, agent-era code exhibits a specific failure mode that prior literature did not name: linguistic inflation. Where human-authored code drifts toward sloppy or inconsistent naming, agent-authored code drifts toward formal-sounding patterns that dominate the training corpus. `Manager`, `Handler`, `Orchestrator`, `Coordinator`, `Provider`, `Service` suffixes proliferate. Synonym clusters emerge where one project vocabulary would do (`user_row`, `user_record`, `user_data`, `customer_obj`). The prior literature frames these as individual-developer mistakes; the agent-era framing treats them as systematic outputs of statistical bias, with different implications for thresholds and remediation.

Put together: the techniques exist, the validation precedent exists, and the failure mode is distinctively visible in modern codebases. The suite earns its place as an exploratory surface.

## Suite properties

Measurement substrate: token stream, identifier splits (camelCase / snake_case), part-of-speech tags, project-local vocabulary dictionaries, small morphological lexicons.

Compute profile: moderate. Most rules run in seconds to minutes. Some use a small pre-trained POS tagger; none require project-wide model training.

Determinism: high. Deterministic given a fixed POS model and a fixed splitter. POS taggers are shipped as pinned artifacts; no network access required at lint time.

Failure modes: domain vocabulary mismatches (a GIS codebase full of `LAS`, `LAZ`, `COPC`, `PDAL` is not degenerate even if a default English dictionary flags it), identifier-splitter edge cases (acronyms, mixed conventions), language-specific naming conventions that violate general morphological rules.

Interpretation burden: medium. A nominalization-density violation requires a sentence of explanation. A synonym-cluster violation requires the reader to see the cluster.

## Candidate rule inventory

Every rule below is a candidate. None ship. Each is paired with the literature grounding that motivated its inclusion and with a proposed investigation phase (see "Investigation ordering" below).

**lexical.nominalization_density** (investigation phase 1)

Proportion of identifiers ending in a small closed set of morphological suffixes: `Manager`, `Handler`, `Controller`, `Orchestrator`, `Coordinator`, `Provider`, `Service`, `Factory`, `Helper`, `Processor`. Normalized by file size or by identifier count. Language-specific suffix lists permitted.

Why it catches what it catches: high nominalization density correlates with the agent-era failure mode where a model produces `UserPreferenceOrchestrationManager` where `UserPreferences` would do. Classical literature does not name this rule but related work on identifier POS tagging (Binkley, Hearn, Lawrie, MSR 2011; Olney et al., ICSME 2016) establishes the technical substrate.

Compute profile: cheap. Pure string suffix match.

Risk: false positives in codebases that legitimately use framework idioms (`RequestHandler`, `ServiceProvider`). Threshold calibration will matter more than the detector.

**lexical.hapax_ratio** (investigation phase 1)

Proportion of identifiers used exactly once in a file or module. High hapax indicates disposable-feeling code where most names exist for a single use site.

Why it catches what it catches: pure corpus statistic from classical corpus linguistics. Closest prior work in software is the identifier-frequency analysis in Lawrie, Feild, Binkley (EMSE 2007).

Compute profile: trivial. One pass.

Risk: small files legitimately have high hapax. Minimum file size must be part of the configuration.

**lexical.vocabulary_growth_deviation** (investigation phase 1)

Heaps' law deviation: fit `V = K × N^β` (vocabulary size V as a power of corpus size N) across files of similar type; flag outliers. Files that blow past the expected curve are lexically bloated; files that underperform are repetitive.

Why it catches what it catches: Heaps' law is foundational corpus linguistics. No direct software-engineering precedent, which is both an opportunity and a calibration burden.

Compute profile: cheap. One curve fit per project per language.

Risk: requires enough files per language per project to fit a stable curve. Small repos will be noisy.

**lexical.cross_module_vocabulary_overlap** (investigation phase 2)

Jaccard or cosine similarity between identifier sets of supposedly independent modules. High overlap between modules that have no import-graph edges indicates implicit coupling that `structural.deps` cannot see.

Why it catches what it catches: lexical coupling in the sense of Abebe et al.'s lexicon-bad-smells catalog, instantiated over the module graph. Prior work: Liu et al. (ICSM 2009) on LCCM (lack of conceptual cohesion of methods) and Nie & Zhang (2012) on topic-based cohesion and coupling.

Compute profile: moderate. Pairwise module comparison.

Risk: high for shared-utility modules. May need explicit "this module is shared" annotations or automated detection of such modules.

**lexical.naming_consistency** (investigation phase 2)

Detect near-synonyms in identifier usage across a project: `user_row` / `user_record` / `user_data` / `customer_obj` for the same concept. Based on Deissenboeck & Pizka's formal model of bijective concept-to-name mappings (Software Quality Journal 2006). Implementation via identifier split, morphological normalization, and project-local dictionary.

Why it catches what it catches: Deissenboeck & Pizka's univocity and mononymy requirements, operationalized without their manual concept-mapping requirement (which made the original tool impractical for existing codebases).

Compute profile: moderate. Project-wide identifier dictionary build plus pairwise near-match detection.

Risk: the gap between "near-synonym by string distance" and "near-synonym by meaning" is where false positives live. Threshold on string distance alone may over-flag.

**lexical.pos_convention_violation** (investigation phase 3)

Part-of-speech convention enforcement: methods should be verb phrases, classes should be nouns, booleans should start with `is`/`has`/`can`/`should`, etc. Detects violations against project-wide POS conventions learned from the corpus itself.

Why it catches what it catches: closest to Allamanis NATURALIZE, restricted to POS conventions. Well-supported by existing POS taggers for code (Binkley/Hearn/Lawrie MSR 2011; Gupta et al. 2013; Olney et al. ICSME 2016; Newman et al. 2020).

Compute profile: moderate. POS tagging per identifier plus project-wide convention inference.

Risk: POS taggers for code are well-characterized but not perfect. Threshold for "convention violation" must account for tagger noise.

## Investigation ordering

Phase 1 (classical statistics, no ML): nominalization density, hapax ratio, vocabulary growth deviation. These need only a tokenizer, an identifier splitter, and elementary statistics. Cheapest to prototype, fastest to evaluate, lowest risk to ship.

Phase 2 (project-local structures): cross-module vocabulary overlap, naming consistency. These need project-wide dictionaries and module-graph analysis but no external models.

Phase 3 (POS tagging): pos convention violation. Needs a pinned POS tagger shipped with slop.

An additional tier beyond phase 3 (embedding-based lexical rules like synonym clustering via identifier embeddings) belongs in the semantic suite rather than here. See `SEMANTIC.md`.

## Per-rule investigation structure

Each candidate rule runs through the same four-step investigation before graduating:

1. **Literature pass.** Trace the concept to its field of origin, confirm terminology, note prior art and operational precedent. Produces a short annotated bibliography.
2. **Formalization.** Define the metric precisely: input, computation, output, units. Matches the rigor of AUx kernel specs.
3. **Empirical probe.** Run a prototype against the reference corpus (see below). Record distribution, outliers, false-positive cases. Produces a notebook or script and a short findings document.
4. **Rule decision.** Ship / shelve / defer. If ship: threshold, severity, config schema, and per-rule documentation page.

A candidate graduates to production only after completing all four steps and meeting the acceptance criteria below.

## Reference corpus

Empirical probes need consistent targets. The proposed reference panel:

- One of the project author's own repositories (known ground truth)
- One well-regarded external open-source library (known clean)
- One sprawling external codebase (known messy)

Specific repositories to be selected before phase 1 begins. Every investigation reuses the same panel so metric behavior can be tracked across the same targets.

## Acceptance criteria for graduation to production

A candidate rule ships in the `lexical.*` namespace only if all of the following hold:

1. Empirical probe across the reference panel produces a signal distribution that separates known-messy from known-clean cases at a tunable threshold. "Tunable" meaning at least one threshold value exists where the messy repo is flagged and the clean repo is not.
2. False-positive rate on the clean reference repository is under 5% at the shipped default threshold, or the rule ships as advisory (`severity = "warning"`) with its default.
3. A one-sentence explanation of what a violation means can be given, suitable for inclusion in the violation output.
4. Language coverage is at least two languages slop already supports structurally (Python, JavaScript, TypeScript, Go, Rust, Java, C#). Language-specific rules are permitted but must be explicitly scoped.
5. Compute cost is bounded: the rule runs in under 30 seconds on the reference panel's largest repo.

Rules that partially meet these criteria may ship as advisory (`severity = "warning"`) with explicit documentation of their calibration status.

## Configuration surface (provisional)

```toml
[rules.lexical]
enabled = false   # suite-wide switch; default off until at least one rule ships

[rules.lexical.nominalization_density]
enabled = false
threshold = 0.15   # proportion; value is a placeholder pending empirical calibration
severity = "warning"

[rules.lexical.hapax_ratio]
enabled = false
threshold = 0.4
severity = "warning"
```

Per-rule threshold names and defaults are placeholders. They will stabilize only after the empirical probe phase of each rule's investigation.

## Relationship to structural, comprehension, and semantic suites

Lexical rules are orthogonal to structural rules. A file can have clean control flow and degenerate vocabulary, or clean vocabulary and tangled control flow. Expect the suites to run together only when a project explicitly adopts lexical checks.

Lexical rules are distinct from comprehension rules (see `COMPREHENSION.md`). A comprehension rule can flag a dense function whose vocabulary is perfectly consistent. A lexical rule can flag inflated or inconsistent vocabulary in code whose information volume is otherwise modest.

Lexical rules are also distinct from semantic rules (see `SEMANTIC.md`). Semantic rules use learned representations (embeddings, topic models, language-model cross-entropy) to capture meaning relationships that go beyond surface-form vocabulary analysis. A lexical rule can detect `UserRow` and `UserRecord` as near-synonyms by string similarity; a semantic rule can detect `fetch_customer` and `get_user` as near-synonyms by embedding similarity. Different substrate, different compute profile, different failure modes.

## Open questions

Not all issues are resolved. The ones most likely to affect the investigation:

- **Domain vocabulary handling.** A GIS codebase needs `LAS`, `LAZ`, `COPC`, `PDAL` in its accepted vocabulary. Should slop support a `.slop-dict` file per project? Auto-infer domain vocabulary from the corpus? Both? This question affects at least three of the candidate rules.
- **Language-specific vs language-agnostic rules.** Nominalization density suffixes are English-centric. Does slop support non-English codebases at all? Does it ship language packs? The lexical suite is where this question becomes unavoidable.
- **Calibration transferability.** Thresholds calibrated on the reference panel may not transfer to other domains. Profiles (`default`, `lax`, `strict`) may need a fourth axis (`domain = generic | embedded | web | data-eng | ...`).

These are noted now so the implementing agent can flag them during investigation rather than ship rules whose defaults silently depend on an unstated assumption.

## Terminology clarification

The suite is **lexical**, not semantic. This matters because "semantic" in program analysis means something else (control and data flow semantics). The research term for what this suite measures is the lexical dimension of code, established by the lexical-smells and linguistic-antipatterns literature cited above. Semantic is reserved for the next suite up.

An earlier version of this plan called this surface "semantic" by mistake. The correction is documented in `TAXONOMY.md` and in the history of this document.
