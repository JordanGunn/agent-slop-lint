# Rule Taxonomy

This doc defines the top-level rule taxonomy for `slop`. All subsequent category-specific and rule-specific docs depend on this one. 

Read this first, then the per-category docs (`STRUCTURAL.md`, `LEXICAL.md`, `SEMANTIC.md`) build on this vocabulary.

---

### 1. Overview

slop currently ships twelve rules organized by implementation concern (`complexity.*`, `class.*`, `hotspots`, `deps`, `packages`, etc). That grouping is historical. It worked when every rule was structural, but it breaks down as slop expands into dimensions of code quality beyond control flow and dependency graphs.

This document defines a three-category taxonomy that scales: **structural**, **lexical**, **semantic**. Every current and future rule belongs to exactly one. The categories are orthogonal, each has a distinct underlying measurement substrate, and the separation matches established software-engineering research terminology (Chidamber & Kemerer, McCabe, Tornhill, Martin for structural; Abebe, Arnaoudova, Lawrie, Deissenboeck for lexical; Hindle, Allamanis, Devanbu for semantic/naturalness).

### 2. The three categories

**Structural rules** measure shape. They operate on control flow, dependency graphs, class hierarchies, and change history. They care about how code is assembled, not what words it uses. Measurement substrates: AST, import graph, inheritance graph, commit history, file size. Output is deterministic from source and git history alone. No models, no embeddings, no external corpora.

**Lexical rules** measure vocabulary. They operate on tokenized identifier streams, docstrings, and comments. They care about the words themselves: are they consistent, concise, appropriately named, drawn from a stable project vocabulary. Measurement substrates: token stream, identifier splits (camelCase / snake_case), part-of-speech tags, project-local dictionaries. Mostly deterministic. Some rules may use a small pre-trained POS model, but no project-wide training is required.

**Semantic rules** measure meaning relationships. They operate on learned or computed representations of what identifiers and code fragments mean relative to each other. They care about cohesion of concepts within a file, drift of vocabulary across modules, alignment between a name and what the code does. Measurement substrates: embeddings (word2vec, FastText, or code-specific), topic models (LDA), language-model cross-entropy. Deterministic given a fixed model and a fixed seed, but the model itself is an external artifact.

The progression structural → lexical → semantic is a progression along three axes simultaneously: increasing compute cost, increasing dependency on external artifacts, and decreasing immediacy of the signal to human intuition. A violation of `complexity.cyclomatic` is obvious. A violation of `lexical.nominalization_density` requires an explanation. A violation of `semantic.identifier_cohesion` requires both an explanation and trust that the underlying embedding model is capturing a real phenomenon.

This progression is intentional. Structural rules are the floor; no project should run without them. Lexical rules are the middle tier; they catch a second axis of rot that structural metrics cannot see. Semantic rules are the ceiling; they catch the deepest phenomena but carry the most caveats about calibration and interpretability.

### 3. Why this specific split

The split is not arbitrary. Each category has a distinct measurement substrate, which determines its compute profile, its failure modes, and the expertise needed to interpret it.

Structural rules run on deterministic tree traversals and graph algorithms. They fail when the parser fails or when the heuristic is miscalibrated for a language idiom (the NPath-vs-dispatch case already documented in CONFIG.md). They can be explained to anyone who has read Fowler.

Lexical rules run on tokenized identifier streams and small NLP primitives (dictionary lookup, POS tagging, morphological suffix detection). They fail when the project uses a legitimate domain vocabulary the rule does not recognize (a GIS codebase full of `LAS`, `LAZ`, `COPC`, `PDAL` is not lexically degenerate even if a default English dictionary flags it). They can be explained to anyone who has read any of the lexical-smell or identifier-naming literature.

Semantic rules run on embeddings or learned models. They fail when the model was trained on a corpus unlike the target project, when the project is too small to establish a stable vocabulary baseline, or when the threshold is calibrated against a different domain. They require calibration work, and their output cannot always be turned into a one-sentence explanation.

Mixing these into one category flattens distinctions that matter. A user who wants to adopt slop gradually should be able to say "start with structural, add lexical once we have a project dictionary, evaluate semantic last." A user in a constrained CI environment should be able to say "skip semantic, the model download is too expensive for our runners." A user debugging a false positive should know, immediately from the category prefix, whether they are debating a parser edge case, a vocabulary edge case, or a model-calibration edge case.

### 4. Rule migration

Every existing rule moves under `structural.*`. No behavior changes, no threshold changes, no new rules. Pure rename.

| Current | New |
|---|---|
| `complexity.cyclomatic` | `structural.complexity.cyclomatic` |
| `complexity.cognitive` | `structural.complexity.cognitive` |
| `complexity.weighted` | `structural.complexity.weighted` |
| `halstead.volume` | `structural.halstead.volume` |
| `halstead.difficulty` | `structural.halstead.difficulty` |
| `npath` | `structural.npath` |
| `hotspots` | `structural.hotspots` |
| `packages` | `structural.packages` |
| `deps` | `structural.deps` |
| `orphans` | `structural.orphans` |
| `class.coupling` | `structural.class.coupling` |
| `class.inheritance.depth` | `structural.class.inheritance.depth` |
| `class.inheritance.children` | `structural.class.inheritance.children` |

CLI conveniences like `slop check complexity` continue to work and mean `slop check structural.complexity`. This is a display-level shorthand, not a second naming scheme. The fully-qualified name is canonical in config, JSON output, and documentation.

### 5. Config surface

The config schema adds one layer of nesting and is otherwise unchanged:

```toml
[rules.structural.complexity]
cyclomatic_threshold = 10
cognitive_threshold = 15
weighted_threshold = 40

[rules.structural.hotspots]
since = "14 days ago"

[rules.lexical]
enabled = false   # planned, not yet shipped

[rules.semantic]
enabled = false   # planned, not yet shipped
```

The `[rules.lexical]` and `[rules.semantic]` sections are reserved now so early adopters can opt in as soon as rules land in those categories. Both default to `enabled = false` until the category has at least one shipped rule with an empirically validated threshold. This matches the pattern `structural.orphans` already uses: advisory categories are off until their false-positive profile is understood.

Profiles (`default`, `lax`, `strict`) remain at the top level. When lexical and semantic rules ship, the profiles will include defaults for them. Until then, the profiles are unchanged.

### 6. Exit codes and severity

Unchanged. All three categories emit violations into the same stream, with the same severity levels (`error`, `warning`) and the same exit codes (0 clean, 1 violations, 2 error). A lexical violation and a structural violation are both violations. The category distinction is for filtering, documentation, and interpretation, not for gating behavior.

An agent or CI consumer processing JSON output should treat `category` as metadata, not as a priority signal. A user who wants to gate their build only on structural rules can do so with `slop check structural`, which is a first-class CLI invocation, not a filter.

### 7. The `orphans` question

`orphans` currently lives under the root as its own rule and is disabled by default. Under the new taxonomy it stays structural (it measures reachability in the reference graph, not lexical or semantic properties). It will move to `structural.orphans`. Its disabled-by-default posture and its advisory-only guidance are unchanged. This is flagged explicitly here because `orphans` is the one rule whose current placement (root-level, no category) most invites confusion.

### 8. What a lexical rule looks like

Concrete preview so the abstract taxonomy has weight. A candidate first lexical rule is **nominalization density**: proportion of identifiers ending in a small closed set of morphological suffixes (`Manager`, `Handler`, `Controller`, `Orchestrator`, `Provider`, `Coordinator`, `Service`), normalized by file size. High nominalization density correlates with the agentic-era failure mode where a model produces `UserPreferenceOrchestrationManager` where `UserPreferences` would do. The full spec and threshold discussion live in the forthcoming `LEXICAL.md`.

### 9. What a semantic rule looks like

Concrete preview, same purpose. A candidate first semantic rule is **identifier embedding cohesion**: variance of identifier embeddings within a file, computed against a pre-trained code embedding model (FastText on subtokens is the current candidate). Low variance suggests the file is focused; bimodal variance suggests it's doing two unrelated things. Flags files whose lexical substance fragments even when structural metrics look fine. Full spec in the forthcoming `SEMANTIC.md`.

### 10. What this document fixes

Two framing errors in earlier conversations that the implementation agent should not inherit:

First, the earlier plan called the new category "semantic." That conflicts with the program-analysis sense of "semantic" (control/data flow). The established research term for what was proposed under that name is **lexical**. Semantic is reserved here for the embedding-and-topic-model tier above lexical, which is a real, distinct layer.

Second, the earlier plan treated "adding semantic rules" as the headline. The headline is the **taxonomy**. Adding rules is downstream. Without the taxonomy, new rules land in whatever category a reviewer names first, and the category boundaries erode. The taxonomy is the commitment; specific rules are instances.

### 11. Downstream dependencies

This document is the parent of three children:

- `STRUCTURAL.md` — describes the structural category, preserves and consolidates the existing CONFIG.md content, notes the rename.
- `LEXICAL.md` — defines the lexical category, catalogs candidate rules with literature backing (Abebe et al., Arnaoudova et al., Allamanis et al., Lawrie et al., Deissenboeck & Pizka), specifies per-rule configuration, and presents the investigation ordering.
- `SEMANTIC.md` — defines the semantic category, catalogs candidate rules with literature backing (Hindle et al., Allamanis et al. survey, IdBench), specifies the external-artifact strategy (pre-trained models, version pinning, offline CI), and presents the investigation ordering.

No rule document should be read without this taxonomy doc first. Any agent or human implementing against slop should be able to answer "which category does this rule belong in, and why?" before writing code.

---

Ready to move to the category documents whenever you are. The next most useful one to produce is `LEXICAL.md` since that's where the first new rules will land, but `STRUCTURAL.md` first might be better if you want to lock in the rename before introducing new surface area. Your call.