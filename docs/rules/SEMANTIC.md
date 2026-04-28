---
status: exploratory
stability: in development
ship_state: planned suite, not shipped; later than lexical
purpose: investigate the applicability and usefulness of semantic rules as a separate slop suite
updated: 2026-04-28
---

# Semantic Rules

> **This document describes a planned suite that depends on external model artifacts.** No semantic rules currently ship in slop. Every rule here is a candidate under active investigation. Unlike the lexical suite, semantic rules require a pre-trained embedding or topic model as an external dependency, which introduces calibration, versioning, and offline-CI concerns that are not yet resolved. The suite will remain exploratory longer than lexical. Expect the rule list, the model strategy, and the configuration surface to evolve. Nothing in this document should be treated as a stable contract.

Semantic rules measure meaning relationships. They operate on learned or computed representations of what identifiers and code fragments mean relative to each other. They care about cohesion of concepts within a file, drift of vocabulary across modules, alignment between a name and what the code does.

This suite sits above the comprehension and lexical suites (see `COMPREHENSION.md` and `LEXICAL.md`) in compute cost, in dependency on external artifacts, and in interpretation burden. It catches phenomena that structural, comprehension, and lexical rules cannot see, but at the cost of non-trivial calibration work.

See `TAXONOMY.md` for the suite system this document fits into. The planned command surface is `slop semantic`; it may share identifier extraction and AST kernels with other suites, but it should not inherit the stable suite's install burden or CI-gate posture.

## Why this suite exists

Some forms of rot are invisible to structural analysis, invisible to surface-form lexical analysis, and visible only to something that understands what words mean relative to other words. Three examples motivate the suite:

A file might contain `fetch_customer`, `get_user`, `retrieve_account`, and `load_profile`. Structurally clean. Not necessarily information-dense. Lexically clean by surface-form analysis because the strings share no substrings. Semantically, these are four names for one operation, and the file is doing one thing under four labels. Only embedding similarity catches this.

A module might be named `auth.py` and contain functions whose implementations are a mix of authentication and request validation. Structurally fine. Lexically fine in isolation. Semantically bimodal: the file's identifier embeddings cluster into two groups, indicating the file is doing two unrelated things. Only embedding variance catches this.

A method named `parse_config` might return `None` on all error paths instead of raising, silently dropping information. Its name promises parsing; its implementation is a lookup-with-swallowing. This is a linguistic antipattern in the Arnaoudova sense, but detecting it requires understanding the semantic gap between "parse" and what the body does. Only language-model-based consistency checking catches this.

None of these three phenomena are new to the research literature. What is new is the opportunity to operationalize them in a general-purpose linter. The naturalness hypothesis (Hindle, Barr, Gabel, Su, Devanbu, ICSE 2012) established that code has statistical regularities exploitable by language models. The Big-Code-and-Naturalness survey (Allamanis, Barr, Devanbu, Sutton, ACM Computing Surveys 2018) cataloged a decade of work applying these techniques to naming, bug detection, and code completion. IdBench (Wainakh, Rauf, Pradel, ICSE 2021) provides a gold-standard benchmark for identifier embedding quality. code2vec (Alon et al., POPL 2019) established that AST-path-based embeddings can represent code semantics. The pieces exist; what's missing is the integration.

## Suite properties

Measurement substrate: embeddings (word2vec, FastText, or code-specific variants like code2vec), topic models (LDA), language-model cross-entropy.

Compute profile: moderate to high. Embedding lookup is fast once a model is loaded. Model loading and any training is the expensive step. For slop's purposes, all models ship as pre-trained, pinned artifacts; no project-specific training is required.

Determinism: deterministic given a fixed model, fixed seed, and fixed inputs. Non-deterministic if the model or seed changes, which is why model pinning is load-bearing for this suite.

Failure modes: model-domain mismatch (a model trained on GitHub Java will underperform on niche domains), threshold transferability (defaults calibrated on the reference panel may not generalize), cold-start for small projects (embedding variance is meaningless below some file count), and interpretation gap (a violation may be correct without being explainable).

Interpretation burden: high. A violation requires the reader to trust the underlying model and to accept that "these two identifiers are semantically close" is not always reducible to a one-sentence explanation.

## External artifact strategy

Semantic rules depend on pre-trained models. slop's approach:

- **Pinning.** Every model ships with a specific version hash. Rule outputs are reproducible across machines given the same slop version.
- **Offline CI.** Models are downloaded at slop install time, not at lint time. A `slop models download` subcommand fetches and caches models. Lint runs do not touch the network.
- **Pluggability.** The model interface is abstract. The first ones shipped will be small (~50-200MB) general-purpose identifier embedding models from established sources (likely FastText trained on a broad code corpus, or the IdBench-evaluated models from Wainakh et al.). Users with compute budget and domain-specific needs can swap in larger or project-trained alternatives via config.
- **Opt-in.** The entire `semantic.*` suite is disabled by default. Projects that want it opt in explicitly. This matches the `orphans` pattern: advisory surfaces with specific adoption friction stay off until a user chooses them.

This strategy will be revisited during phase 1 of the investigation. The offline-CI requirement is the most likely to force changes.

## Candidate rule inventory

Every rule below is a candidate. None ship. Semantic rules are expected to mature later than lexical rules because of the model-strategy work. The investigation phases below are sequenced accordingly.

**semantic.identifier_cohesion** (investigation phase 1)

Variance of identifier embeddings within a file. Low variance indicates the file is focused on one concept. Bimodal variance indicates the file is doing two unrelated things.

Why it catches what it catches: operationalizes conceptual cohesion in the sense of Liu et al. (ICSM 2009, LCCM) and the topic-based cohesion work of Nie & Zhang (2012). Uses identifier embeddings rather than topic models because embeddings are better characterized and easier to pin.

Compute profile: moderate. Embedding lookup for every identifier in a file, variance computation.

Risk: files below a minimum identifier count produce unreliable variance. Threshold needs calibration per language because different languages produce different embedding distributions for the same conceptual content.

**semantic.synonym_clustering** (investigation phase 1)

Project-wide identifier embedding clustering. Flag files containing N or more near-synonym clusters. Catches the `user_row / user_record / user_data / customer_obj` case that surface-form lexical analysis misses.

Why it catches what it catches: operationalizes Deissenboeck & Pizka's mononymy requirement (one concept, one preferred term) using embeddings rather than manual concept mapping.

Compute profile: moderate. One-time project-wide identifier embedding precompute, then clustering and per-file reporting.

Risk: clusters that are semantically similar but intentionally distinct (for example, a data pipeline where `raw_user`, `cleaned_user`, `enriched_user` are genuinely different concepts) will produce false positives. May need annotation escape hatches.

**semantic.cross_module_conceptual_coupling** (investigation phase 2)

Topic-model overlap between modules that share no import-graph edges. Generalizes `lexical.cross_module_vocabulary_overlap` from surface-form vocabulary to latent topics. A stronger signal for hidden coupling where modules use different words for the same concept.

Why it catches what it catches: direct operationalization of Nie & Zhang (2012) cohesion-and-coupling via topic modeling.

Compute profile: high. LDA or equivalent topic model fit across the project, per-module topic distributions, pairwise comparison.

Risk: LDA sensitivity to hyperparameters is well-documented (Binkley et al., ICPC 2014; Agrawal et al., 2018). Configuration surface will need careful bounding to avoid exposing LDA tunables to end users.

**semantic.name_implementation_alignment** (investigation phase 3)

Per-function distance between the function name's embedding and an embedding of its body or its docstring. High distance indicates the name does not match what the function does.

Why it catches what it catches: directly operationalizes a subset of Arnaoudova et al.'s linguistic antipatterns (name/type mismatch, unexpected side effects, missing-implied-return-type) using embeddings rather than the rule-based detectors used in LAPD. Related to NATURALIZE's method-naming work (Allamanis et al., Suggesting Accurate Method and Class Names, ESEC/FSE 2015).

Compute profile: high. Body embedding per function, name embedding per function, distance computation. The body embedding is the expensive step and may require code2vec or a similar AST-path embedding rather than identifier embeddings.

Risk: this is the most powerful and the most speculative rule in the suite. Implementation bodies vary enormously in size and content, and a name/body distance threshold that works across diverse codebases is not guaranteed to exist. Likely ships as advisory even in the best case.

## Investigation ordering

Phase 1 (identifier-embedding rules): identifier cohesion, synonym clustering. These need a single pre-trained identifier embedding model. The compute and strategy decisions for a general embedding model, once made, unlock both rules.

Phase 2 (topic-model rules): cross-module conceptual coupling. Needs LDA infrastructure and careful hyperparameter handling.

Phase 3 (language-model and code-embedding rules): name-implementation alignment. Needs code2vec-class embeddings or a lightweight LM for body-vs-name scoring. Longest investigation.

## Per-rule investigation structure

Same four-step process as the lexical suite (see `LEXICAL.md`):

1. Literature pass.
2. Formalization.
3. Empirical probe against the reference corpus.
4. Rule decision (ship / shelve / defer).

Semantic rules have one additional pre-phase step: **model selection**. Before any phase 1 rule can be prototyped, the team must pick the pre-trained identifier embedding model, document its provenance, pin its version, and validate its behavior on a small controlled sample (for example, IdBench's human-labeled identifier pairs). This is a one-time cost that unlocks multiple rules, but it must be paid before phase 1 begins.

## Reference corpus

Same reference panel as the lexical suite. Semantic rules additionally benefit from IdBench's labeled identifier pairs for model validation, independent of the project reference panel.

## Acceptance criteria for graduation to production

A candidate semantic rule ships in the `semantic.*` namespace only if all of the following hold:

1. The underlying model is pinned, its version is documented, and its download-install-verify cycle is reproducible.
2. Empirical probe across the reference panel produces a signal distribution that separates known-messy from known-clean cases at a tunable threshold.
3. False-positive rate on the clean reference repository is under 5% at the shipped default threshold, or the rule ships as advisory.
4. The rule ships with a short explainer that describes what a violation means in terms a user can act on, even if the underlying computation is not fully explainable.
5. Language coverage is at least two languages slop already supports structurally.
6. Compute cost is bounded: the rule runs in under 60 seconds on the reference panel's largest repo, given a pre-loaded model.

Semantic rules are expected to ship more conservatively than lexical rules. Advisory-by-default is the baseline posture; any semantic rule that ships as `severity = "error"` will need strong empirical justification.

## Configuration surface (provisional)

```toml
[rules.semantic]
enabled = false   # suite-wide switch; default off
model = "fasttext-code-general-v1"   # pinned pre-trained model; placeholder name

[rules.semantic.identifier_cohesion]
enabled = false
max_variance = 0.7
min_identifiers = 20
severity = "warning"

[rules.semantic.synonym_clustering]
enabled = false
min_clusters_per_file = 3
similarity_threshold = 0.85
severity = "warning"
```

Threshold names and defaults are placeholders. They will stabilize only after the empirical probe phase of each rule's investigation and after model selection is finalized.

## Relationship to lexical and structural suites

Semantic rules are the ceiling of the planned taxonomy: the most powerful and the most caveated. They catch phenomena the other suites cannot see, but they carry costs the others do not:

- External artifacts (pinned models) with their own versioning and distribution concerns.
- Calibration that does not transfer as cleanly across domains as structural or lexical thresholds.
- Interpretation burden that cannot always be reduced to a one-sentence explanation.

Expect semantic rules to be the last suite a project adopts. Expect most projects to run structural only, or structural plus carefully selected comprehension/lexical checks, and never enable semantic. That is a valid end state. Semantic rules exist for projects where the other suites have matured and a further axis of measurement earns its cost.

## Open questions

The semantic suite has more unresolved questions than the other planned suites. The ones most likely to affect the investigation:

- **Model choice.** FastText on subtokens, code2vec, or something else? Each has different coverage, cost, and licensing profiles. Decision will be made during the model-selection pre-phase.
- **Offline CI viability.** Can a 100-200MB model ship with slop without burdening users who never enable the semantic suite? Lazy download is the leading candidate but has install-time UX implications.
- **Determinism audit.** Some embedding models have subtle non-determinism (thread-level floating-point variance). The audit needed to certify a chosen model as deterministic for slop's purposes is non-trivial.
- **Licensing.** Pre-trained models come with licenses that interact with slop's Apache 2.0 license. This is a legal question, not a technical one, but it affects which models are viable.
- **Domain transferability.** A model trained on mainstream GitHub corpora will underperform on specialized domains (embedded firmware, niche scientific code, game engine code). Does slop need domain-specific model packs, or does it accept that semantic rules are a "works for mainstream codebases" feature?

These are flagged now so the implementing agent can raise them during investigation rather than inherit unstated assumptions.

## Relationship to lexical rules

The boundary between lexical and semantic is real but fuzzy. Two guiding heuristics:

- If the rule works with string operations and small morphological lexicons, it is lexical.
- If the rule needs a pre-trained embedding or topic model to compute its core signal, it is semantic.

`lexical.naming_consistency` (near-synonyms by string distance) and `semantic.synonym_clustering` (near-synonyms by embedding distance) are the clearest illustration of the distinction. They target the same phenomenon with different substrates, produce different false-positive profiles, and carry different operational costs. Both may ship; they are not redundant.
