## Lexicon Subsystem — first-class, linter-independent

The legacy lexical capability was tangled the way the AST was: `lexicon/view.py`
(~950 lines) mixed token-space measurement with AST walks and rule policy, with the
algorithm primitives spread across several sibling modules. This subsystem gives
identifier vocabulary one owner — and, like `ast/`, makes it a package that can
stand on its own.

### Principle

`lexicon/` is **strictly the linguistic kernel**: a self-contained
vocabulary-analysis library over a corpus of identifier tokens. It tokenizes,
counts, measures distribution, and compares — in the vocabulary of lexicography,
not of slop. The governing test for every member: *would a corpus linguist
recognize this concept independent of slop?* Hapax ratio, type/token counts, Zipf
shape — yes. Threshold verdicts — no; those are slop's policies and live at a
higher layer. The litmus is hard: **`lexicon/` must be importable and
usable outside the linter** (it powers the claim-free `vocabulary` observation),
so it imports nothing from `component`, `rules`, or `linter`.

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
                       linter/              (rules; thresholds + verdicts)
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

This dissolves the direct AST walks in the legacy lexical layer
(`view.body_token_locations` and the rule-private traversals), both of which
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
  corpus.py        Lexicon: tokens, counts, hapax_ratio, most_common, frequencies, slice
  distribution.py  Zipf fit + TokenDistribution + narrate() (claim-free evidence)
  comparison.py    jaccard / containment / cosine / js_divergence over frequency maps
```

### The boundary: lexicon owns vocabulary, the layer above owns metrics

The AST line was "navigation vs math." The lexicon line is:

> **Lexicon owns the token-space and its descriptive linguistic measurements.
> Slop's named metrics, thresholds, and verdicts live above it.**

`lexicon/` provides the Zipf shape, the hapax ratio, and the frequency counts. The
rule layer composes them into slop's signals — the `vocabulary` observation's
narration is the shipped consumer. The risk to avoid is the lexical form of the v2
sin — the kernel absorbing rule policy. A threshold or a verdict in `lexicon/` is
the tell.

### Dependency posture — zero new runtime deps

A survey of Python lexical libraries (verified for maintenance / license / fit,
2025–2026) confirms the kernel stays hand-rolled and self-contained — the whole
point is that it is *code-specific*, not natural-language, analysis:

- **frequency / hapax / Zipf** — `Counter` + a ~10-line OLS log-log fit; `powerlaw`
  would pull numpy + scipy + matplotlib for nothing.
- **stop-words** — curated and code-specific; a generic English list would *hurt*
  (it suppresses identifier-common words and misses SE boilerplate).

The one capability a library *could* add — Ronin-class abbreviation splitting
(`getHTTPResponse → [get, http, response]`) — has no maintained, permissively
licensed option (`spiral` is archived, GPL-3, NLTK-bound); logged as an optional
future hand-roll, not a port requirement.

### Migration path (mirrored the AST attrition)

`Span` moved to the shared base; `ast` grew `Node.identifiers()`; `lexicon/` stood
up from the string-pure inventory (`distribution.py` ports verbatim); the component
bridge (`scope/lexicon.py`) wires them. The kernel is proven on the `vocabulary`
observation; anything further migrates by attrition, lifting slop's named metrics
up as rules.

### Inventory Ledger

# Lexicon Subsystem — Inventory & Porting Ledger

Companion to `INVENTORY.md`. The kernel shipped as `src/slop/lexicon/`; the rule
layer that consumed the rest of the legacy lexicon was cut with the coined rules
(see CHANGELOG), so this ledger records the shipped surface plus the deferred
remainder, not planned ports.

**The boundary** is sharper than "descriptive vs verdict": it is **general
linguistic concept → lexicon; slop-invented metric → higher layer.** Litmus for
every row: *would a corpus linguist recognize this concept independent of slop?*
If yes → lexicon (renamed to lexicographic language). If it is slop's coinage,
composition, or threshold → higher layer. The hard requirement behind the boundary:
`lexicon/` must be importable and usable **outside the linter**.

## Shipped surface (`src/slop/lexicon/`)

| Module | What it computes |
|---|---|
| `tokenize.py` | `split_tokens` (camel/snake → word tokens) + `Lexeme` (tokenised identifier + provenance) |
| `stopwords.py` | `STOP_WORDS` — Newman-14 universal noise + identifier glue; injectable |
| `roles.py` | `Role` enum (`REALM / PACKAGE / MODULE / CLASS / CALLABLE / PARAMETER / BODY_REF`) |
| `corpus.py` | `Lexicon` — the analysable token-space: `tokens`, `significant_token_count`, `total_token_count`, `hapax_ratio`, `most_common`, `frequencies`, `slice` |
| `distribution.py` | `_zipf_fit` (α, R²) + `TokenDistribution` (spectrum, hapax, head concentration) + `narrate()` — the claim-free evidence the `vocabulary` observation emits |
| `comparison.py` | `jaccard` / `containment` / `cosine` / `js_divergence` / `js_similarity` over frequency maps |

## Deferred

| Item | Disposition |
|---|---|
| Ronin / abbreviation splitting | optional future hand-roll; no maintained permissive lib (`spiral` is archived/GPL-3/NLTK-bound) |

## Dependency decisions (verified library survey, 2025–2026)

Net: **zero new runtime deps.** The kernel stays hand-rolled and self-contained.

| Operation | Decision | Why |
|---|---|---|
| camel/snake split | hand-roll | ~5 lines (`split_tokens`) |
| abbreviation splitting (Ronin) | defer / future hand-roll | `spiral` archived + GPL-3 + NLTK-bound |
| frequency / hapax / Zipf | hand-roll | `Counter` + ~10-line OLS; `powerlaw` pulls numpy+scipy+matplotlib |
| stop-words | hand-roll (curated) | no code corpus; NLTK English list actively *hurts* identifiers |
| vocab modeling | hand-roll | `Counter[str]` is the correct identifier vocabulary model |

## Open questions

- **`Role` membership** — `BODY_REF` granularity, whether `REALM` is needed —
  finalize when wiring the bridge.
- **Final naming** — confirm `distribution` / `slice` read well
  in situ before locking the public surface.