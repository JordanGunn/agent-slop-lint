## Lexicon Subsystem — first-class, linter-independent

The legacy lexical capability is sprawled the way the AST was: `lexicon/view.py`
(~950 lines) mixes token-space measurement with AST walks and rule policy, and the
algorithm primitives are scattered across `affix.py` / `clusters.py` / `actions.py`
/ `profile.py` / `diagnostic/`. This subsystem gives identifier vocabulary one
owner — and, like `ast/`, makes it a package that can stand on its own.

### Principle

`lexicon/` is **strictly the linguistic kernel**: a self-contained
vocabulary-analysis library over a corpus of identifier tokens. It tokenizes,
counts, measures distribution, and clusters — in the vocabulary of lexicography,
not of slop. The governing test for every member: *would a corpus linguist
recognize this concept independent of slop?* Hapax ratio, type/token counts, Zipf
shape, collocations, formal concepts, edit-distance clustering — yes. "imposters",
"sprawl", "hammers", threshold verdicts — no; those are slop-invented metrics and
live at a higher layer. The litmus is hard: **`lexicon/` must be importable and
usable outside the linter** (it powers a future vocabulary visualizer and the
claim-free `vocabulary` observation), so it imports nothing from `component`,
`rules`, or `linter`.

This is the same discipline as `ast/`, but `lexicon/` is a *domain* package, not a
*proxy*: it isolates algorithms we own, not a foreign dependency. So it has no
`Node.raw` analog (nothing foreign to escape to) and needs no cross-language
neutralization layer — a lowercased token is already language-agnostic, so the
`NodeKind` problem does not recur here.

### Layering (`lexicon/` is a bottom-layer peer of `ast/`)

```text
                         span.py            (shared location primitive)
                        /        \
                     ast/        lexicon/   ← peers; neither imports the other
                        \        /
                     component/             (wires AST identifiers → (text,role,span); unions fs names)
                          ↑
                       linter/              (rules; slop-invented metrics + batteries)
```

`Span` moves down once more — out of `ast/` to a shared base both `ast/` and
`lexicon/` depend on. `Span` was never an AST type; it is the substrate's
source-location primitive, and the moment a second bottom-layer package needs it,
keeping it in `ast/` would force `lexicon → ast`. (Same move that earlier pushed
`Span` out of `component/` to break the `component ⇄ ast` cycle, applied one level
further.)

### The interface — plain data, role-tagged

Nothing AST-shaped crosses into `lexicon/`. Its input is a stream of plain units:

```python
(text: str, role: Role, span: Span)
```

`Role` is a **lexicon-owned** enum — `MODULE | PACKAGE | CLASS | CALLABLE |
PARAMETER | BODY_REF` — *not* `component.ComponentKind` (importing that would
couple lexicon upward). The bridge maps `ComponentKind` + identifier position →
`Role`. Role-tagging is load-bearing: `named_entities` needs callable/class names,
first-name clustering needs parameters, scope-overlap needs body references — all
expressed without a single AST node crossing the boundary. This is the one place
the "just a list of strings" instinct needed enrichment: still plain data, but
role-tagged.

The bridge is **option A**: `ast/` grows

```python
Node.identifiers() -> Iterator[tuple[str, Span]]
```

— pure navigation + text + span, squarely within the AST's charter (it already
classifies `IDENTIFIER`). The component layer calls it, tags each unit with a
`Role`, and unions the filesystem-derived names (module/package/realm — absent
from the AST but carrying the grammatical-degradation signal). `ast` yields the
identifier *as written*; splitting `fooBar → [foo, bar]` is lexical and stays
lexicon's job. The clean seam: **ast gives words as written; lexicon decides what
counts as vocabulary.**

This dissolves the *only* two direct AST walks in the entire legacy lexical layer —
`view.body_token_locations` and `stutter`'s hand-rolled traversal — both of which
wanted exactly "identifier tokens + location under a subtree."

### Casing — normalized away, not measured

The tokenizer is **convention-blind**: `split_tokens` splits camelCase, snake_case,
PascalCase, acronym runs, and digit boundaries uniformly, with no knowledge of what
convention an identifier *should* follow; `Lexicon` lowercases on construction, so
case is erased before any measurement. The kernel therefore needs no `Case` enum and
must **not** bind to a language's declared casing convention (e.g. "Python classes are
PascalCase") — that coupling is fragile (developers violate conventions: camelCase in
Python, PascalCase fields), and the kernel does not need the convention to measure
vocabulary. Casing-convention *violation* is a style signal, not structural debt — the
kind agents self-correct — so detecting it is a deliberate non-goal here. If a rule
ever wants it, it operates on the case-bearing form above the kernel, before
normalization; the kernel measures words, not their presentation.

### Package layout

```text
lexicon/
  stopwords.py     curated code stop-word list (Newman-14 + glue); injectable
  tokenize.py      split_tokens (camel/snake) + Lexeme
  roles.py         Role enum
  frequency.py     type/token counts, hapax ratio, frequency distribution
  distribution.py  Zipf fit + TokenDistribution + narrate() (claim-free evidence)
  sets.py          alphabet / coverage / overlap / dispersion
  collocations.py  co-occurrence + association (was "packets") + isolates
  affix.py         single-substitution edit distance + affix-pattern clustering
  concepts.py      Formal Concept Analysis (extent/intent) + concept inheritance
  corpus.py        Lexicon: the analyzable token-space; partition / filter / slice
```

### The boundary: lexicon owns vocabulary, the layer above owns metrics

The AST line was "navigation vs math." The lexicon line is:

> **Lexicon owns the token-space and its descriptive linguistic measurements.
> Slop's named metrics, thresholds, batteries, and verdicts live above it.**

`lexicon/` provides FCA, collocations, affix clustering, Zipf shape. The rule layer
*composes* them into slop's signals — "sprawl" (FCA over affix clusters above an
alphabet floor), "hammers" (banlist over collocation isolates), "stutter"
(scope-token overlap). The renamed primitives stay neutral; the coinages stay up.
The risk to avoid is the lexical form of the v2 sin — the kernel absorbing rule
policy. A threshold or a verdict in `lexicon/` is the tell.

### Cross-view batteries are rules, joined by `Span`

Three legacy rules are not lexical — they are batteries that join vocabulary to
*structure*: `imposters` / `slackers` (first-parameter clusters discriminated by
body-Jaccard + receiver-call density) and `vocabulary`'s displacement gate (token
ownership vs the import graph). The fat legacy `FirstParameterCluster` — lexical
membership **+** structural enrichment **+** verdict in one record — splits three
ways: `lexicon` emits the lexical clusters (groups of names); `structure` measures
the bodies; the **rule** joins them, looking each member up *by `Span`*, and owns
the verdict. The shared `Span` primitive doubles as the cross-view join key. Where
the structural halves live (a `structure` view method vs rule-private) is deferred
with the structure-package design.

### Dependency posture — zero new runtime deps

A survey of Python lexical libraries (verified for maintenance / license / fit,
2025–2026) confirms the kernel stays hand-rolled and self-contained — the whole
point is that it is *code-specific*, not natural-language, analysis:

- **edit distance** — the operation is a *single-substitution* check on equal-length
  token tuples, not general Levenshtein; already optimal hand-rolled. (`rapidfuzz`
  is excellent and MIT but unneeded; revisit only if similarity is generalized.)
- **FCA** — keep the existing `compute_concepts`; the one MIT lib (`concepts`) is
  maintenance-stale (2020) and we already own a working string-pure implementation.
- **frequency / hapax / Zipf** — `Counter` + a ~10-line OLS log-log fit; `powerlaw`
  would pull numpy + scipy + matplotlib for nothing.
- **collocations** — `Counter` over token pairs + PMI; NLTK is prose-oriented.
- **stop-words** — curated and code-specific; a generic English list would *hurt*
  (it suppresses identifier-common words and misses SE boilerplate).

The one capability a library *could* add — Ronin-class abbreviation splitting
(`getHTTPResponse → [get, http, response]`) — has no maintained, permissively
licensed option (`spiral` is archived, GPL-3, NLTK-bound); logged as an optional
future hand-roll, not a port requirement.

### Migration path (mirror the AST attrition)

Docs first (this pass: this section, with the inventory ledger appended below).
Then, when built: extract `Span` to the shared base; add `ast` `Node.identifiers()`; stand up
`lexicon/` from the string-pure inventory (most of `affix.py` / `distribution.py`
ports verbatim, renamed); wire the component bridge; prove on the `vocabulary`
observation and `stutter` (the cleanest consumers) against current measurements;
then migrate the rest by attrition, lifting slop's named metrics up as rules.

### Inventory Ledger

# Lexicon Subsystem — Inventory & Porting Ledger

Companion to `INVENTORY.md`. Maps every legacy `src/slop/lexicon/*` primitive and
the 7 lexical rules to its home in the v3 top-level `lexicon/` package. Source of
truth for *what lexical compute moves where*; `DESIGN.md`'s "Lexicon Subsystem"
section is the source of truth for *how the package is shaped*.

**The boundary** is sharper than "descriptive vs verdict": it is **general
linguistic concept → lexicon; slop-invented metric → higher layer.** Litmus for
every row: *would a corpus linguist recognize this concept independent of slop?*
If yes → lexicon (renamed to lexicographic language). If it is slop's coinage,
composition, or threshold → higher layer. The hard requirement behind the boundary:
`lexicon/` must be importable and usable **outside the linter**.

## Status legend

- **port** — relocate into `lexicon/`, renamed to neutral lexicographic language; already string-pure.
- **rule** — slop-invented metric / threshold / verdict; lives at the layer above `lexicon/` (TBD — possibly under `linter/`).
- **cross-cut** — a battery that joins a lexical signal to a *structural* one; a rule consuming `lexicon` **and** `structure`, keyed by `Span`.
- **defer** — research scaffolding, corpus-blocked, or optional-future; not ported this pass.
- **dissolve** — the legacy AST walk it performed is replaced by `ast` `Node.identifiers()`.

---

## 1. PORT-TO-LEXICON — the linguistic kernel

All string-pure today; relocate and rename to lexicographic terms.

| Legacy symbol | Module | What it computes | New name | Note |
|---|---|---|---|---|
| `split_tokens` | tokens.py | camel/snake → word tokens | `tokenize` / `split_tokens` | core plumbing |
| `UNIVERSAL_NOISE` | affix.py | Newman-14 SE boilerplate + glue | `STOP_WORDS` (default) | injectable; code-curated |
| `Lexeme` / `Lexeme.of` | affix.py | tokenised identifier + provenance | `Lexeme` | keep |
| `tokens` / `frequencies` / `modal_tokens` | view.py | type list / freq Counter / top-k | `types` / `frequencies` / `most_frequent` | — |
| `hapax_ratio` | view.py | fraction of types occurring once | `hapax_ratio` | canonical lexicostat |
| `alphabet` | view.py | distinct type set | `alphabet` | — |
| `coverage` | view.py | fraction of types in an external vocab | `coverage` | — |
| `overlap` | view.py | Jaccard between two lexicons' alphabets | `overlap` | — |
| `token_locations` | view.py | type → set of spans (dispersion) | `dispersion` | base for "spread" |
| `cooccurrences` | view.py | (a,b) → count over bags | `co_occurrences` | — |
| `packets` | view.py | co-occurrence clusters ≥ assoc. threshold | `collocations` | **rename** (slop coinage) |
| `packet_isolates` | view.py | types in no collocation | `collocation_isolates` | rename; primitive only |
| `callable_token_bags` / `file_token_bags` | view.py | one token-set per unit | `bags(by=…)` | per-unit grouping |
| `by_file` / `by_package` | view.py | sub-lexicon per file / dir | `partition(key)` | **neutralize** ("package" is a code concept; partition by a span attribute) |
| `under` / `where` / `slice` | view.py | filtered sub-lexicon | `filter` / `slice` | corpus selection |
| `named_entities` | view.py | name-bearing units, token-split | `named_entities` | view over role-tagged input |
| `token_edit_distance_1` | affix.py | single-substitution check on equal-len token tuples | `single_substitution` | **not** general Levenshtein |
| `build_affix_patterns` / `patterns_by_alphabet` | affix.py | Levenshtein-1 pattern grouping + alphabet clustering | `affix_patterns` / `cluster_by_alphabet` | — |
| `compute_concepts` | affix.py | FCA: (extent, intent) closed pairs | `formal_concepts` | hand-rolled FCA (kept) |
| `find_inheritance_pairs` | affix.py | strict subconcept pairs | `concept_inheritance` | — |
| `AffixPattern` / `AffixCluster` / `FCAConcept` | affix.py | algorithm records | (same) | data records |
| `TokenDistribution` / `token_distribution` / `_zipf_fit` | distribution.py | Zipf fit (α, R², spectrum, hapax) | `distribution` | + norm constants |
| `TokenDistribution.narrate()` | distribution.py | claim-free evidence prose | `narrate()` | the observation emitter |
| `summary` / `histogram_buckets` / `log_buckets` / `Summary` / `HistogramBin` | distribution.py | generic numeric stats | (internal) | distribution support |
| `package_distributions` | namespace.py | per-partition distribution, ranked | `partition_distributions` | rename; via `partition` |
| `_jaccard` / `_modal_tokens` / `_overlap` | profile.py | set/token helpers | (internal) | plumbing |
| `NamedEntity` | records.py | name-bearing unit record | `NamedEntity` | data record |

---

## 2. MOVE-TO-RULES — slop-invented metrics

Composes kernel primitives with slop policy/thresholds; lives above `lexicon/`.

| Legacy symbol | Module | Why it's a rule |
|---|---|---|
| `sprawl_over` | affix.py | "sprawl" is a slop coinage — FCA-over-affix-clusters above an alphabet floor; engine of the `sprawl` rule. (Primitives it calls stay in lexicon.) |
| `frequency_head` (p90 cut) | view.py | a frequency *cut* tuned for `verbosity`; lexicon exposes `frequencies`/`distribution`, the rule takes the slice |
| `spread_dominant` / `middle_spread` | view.py | spread *cuts* tuned for rules; lexicon exposes `dispersion`, the rule applies the threshold |
| `classify_cluster` + `_FALSE_POSITIVE_NAMES` + `_INFRASTRUCTURE_NAMES` | profile.py | hardcoded policy name-sets emitting a verdict string |
| `map_packet` / `map_packets_to_actions` / `CorrectiveAction` | actions.py | corrective advisories (prescriptions) |
| `split_packets_by_class_ownership` | filters.py | "conventional = owned by a class" is an architectural policy judgment |
| `verdict` / `profile_label` fields | records.py | rule output baked into a record |

---

## 3. CROSS-CUTTING — batteries (rule joins lexicon + structure by `Span`)

The fat `FirstParameterCluster` splits: lexical clusters → `lexicon`; structural
enrichment → `structure`; verdict → the rule, joining members by `Span`.

| Legacy symbol | Module | Lexical half (→ lexicon) | Structural half (→ structure / rule) |
|---|---|---|---|
| `compute_first_param_clusters` | clusters.py | group names by key + sub-cluster by prefix | "by first parameter" framing; body lookup |
| `profile_cluster` / `_signature_ngrams` / `_receiver_call_count` | profile.py | — | body-shape n-gram Jaccard; receiver-call density (walks AST bodies) |
| `FirstParameterCluster` | records.py | members, param name, name-tokens, scope hapax | `body_jaccard_mean`, `mean_receiver_calls`, verdict |
| `concept_ownership` / `ConceptOwnership` | namespace.py / distribution.py | per-type owner concentration | import dependency graph (displacement gate) |

Where the structural halves live (a `structure` view method vs rule-private) is
**deferred to the structure-package design** — out of scope this pass.

---

## 4. DROP-OR-DEFER

| Legacy symbol | Module | Disposition |
|---|---|---|
| `report` | diagnostic/__init__ | defer — research harness that *executes rules* |
| `count_by_scope` / `with_cells` | diagnostic/violations | defer — rule harness |
| `ScopedViolationCount` / `ViolationCell` / cell-tagging / `format_cells` | diagnostic/violations | defer — portable but no consumer; research scaffolding |
| `ConceptOwnership.verdict()` | distribution.py | defer — uncalibrated; **concept-escape is corpus-blocked** (see `project_concept_escape_status`) |
| Ronin / abbreviation splitting | (new) | defer — optional future hand-roll; no maintained permissive lib (`spiral` is archived/GPL-3/NLTK-bound) |

---

## DISSOLVE — replaced by `ast` `Node.identifiers()`

| Legacy symbol | Module | Replacement |
|---|---|---|
| `body_token_locations` / `_callable_body_tokens` / `_walk_identifier_nodes` | view.py | `Node.identifiers() -> Iterator[(str, Span)]`, tagged `role=BODY_REF` |
| `stutter`'s own `parse.root_node` walk | linter/rules/stutter.py | same — consumes the `(text, role, span)` stream |

These two were the **only** direct AST walks in the entire legacy lexical layer.

---

## Consumer contract — the 7 lexical rules

The public surface the kernel must expose (5 clean lexical consumers; 2.5 cross-cutting).

| Rule | Lexicon primitives needed | Non-lexical signal | Output |
|---|---|---|---|
| stutter | `split_tokens`, `dispersion`, body refs (via `identifiers`) | none | verdict |
| verbosity | `named_entities`, `dispersion`, `frequencies` (head cut derived in-rule) | lang-id token discount only | verdict |
| hammers | `named_entities`, `dispersion`, `collocation_isolates`, `files`, `split_tokens` | none | verdict |
| sprawl | `Lexeme`s, `formal_concepts`, `affix_patterns`, `concept_inheritance` | none (first-param only to suppress) | verdict |
| imposters | first-param name clusters (lexical) | **body-Jaccard, receiver-call density** | verdict · **cross-cut** |
| slackers | first-param clusters, `affix_patterns` coverage | profile gate carries structural | verdict · **cross-cut** |
| vocabulary | `distribution`, `partition_distributions` | dependency graph (displacement — deferred) | observation · partial cross-cut |

---

## Dependency decisions (verified library survey, 2025–2026)

Net: **zero new runtime deps.** The kernel stays hand-rolled and self-contained.

| Operation | Decision | Why |
|---|---|---|
| camel/snake split | hand-roll | ~5 lines (already have `split_tokens`) |
| abbreviation splitting (Ronin) | defer / future hand-roll | `spiral` archived + GPL-3 + NLTK-bound |
| edit distance | hand-roll (single-substitution) | the op is single-swap, not general Levenshtein; `rapidfuzz` declined (unneeded) |
| FCA | keep `compute_concepts` | `concepts` is MIT but 2020-stale; we own a working string-pure impl |
| frequency / hapax / Zipf | hand-roll | `Counter` + ~10-line OLS; `powerlaw` pulls numpy+scipy+matplotlib |
| collocations | hand-roll | `Counter` over pairs + PMI ~15 lines; NLTK is prose-oriented |
| stop-words | hand-roll (curated) | no code corpus; NLTK English list actively *hurts* identifiers |
| vocab modeling | hand-roll | `Counter[str]` is the correct identifier vocabulary model |

---

## Open questions

- **Where the higher metric layer lives** — under `linter/` or a dedicated metric
  package — is undecided (deliberately deferred).
- **Battery structural halves** (`body_jaccard`, `receiver_density`, displacement)
  — `structure` view methods vs rule-private — deferred with the structure design.
- **`Role` membership** — `BODY_REF` granularity, whether `REALM` is needed —
  finalize when wiring the bridge.
- **Final naming** — confirm `collocations` / `dispersion` / `partition` read well
  in situ before locking the public surface.


