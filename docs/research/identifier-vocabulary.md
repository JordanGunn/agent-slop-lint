# Identifier vocabulary: layered ignore lists from the literature

slop's lexicon work needs defensible defaults for "words to ignore"
when computing token frequencies, modal tokens, and alphabet
detection over identifier streams. Hand-curating one flat list
invites bias and risks silencing the rules that exist precisely to
catch certain kinds of vocabulary (e.g. `lexical.hammers` flags
`Manager`, `Helper`, `Service` — putting those in a global ignore
list would defeat the rule).

The literature gives us two principles and one empirical seed.

## Two principles (Fan, Arora & Treude 2023)

In *"Stop Words for Processing Software Engineering Documents: Do
they Matter?"* the authors derived 200 SE-domain stop words from
10,000 Stack Overflow questions using TF-IDF and Poisson methods.
Their findings:

1. **No universal list exists.** *"It is not possible to have a
   standard list of stop words. The semantics of each word are
   different in each domain. The context of the task needs to be
   taken into account."*
2. **Binary removal can hurt.** SE-domain lists outperformed
   generic lists on 17 of 19 metrics across three downstream
   tasks — but generic large lists *degraded* performance in some
   tasks by removing valuable words. They flag weighted /
   attenuated approaches as a limitation they did not address.

Fan's specific 200-word list is *not directly usable* for slop's
identifier-token analysis: their corpus is Stack Overflow prose,
not identifier streams. A word noisy in SO questions (`code`,
`function`, `method`) is exactly the discriminative content we want
preserved when analysing names. We adopt the principles, not the
list.

## One empirical seed (Newman et al. 2017)

In *"Lexical Categories for Source Code Identifiers"* the authors
categorised 480K unique identifiers across **50 open-source C/C++
systems** (80–2400 KLOC each — Apache, Boost, Clang, GIMP, OpenCV,
etc.). In Research Question 3 they searched for identifier names
appearing in *all 50* systems studied. They found **14**:

> `a`, `length`, `id`, `pos`, `start`, `next`, `str`, `key`,
> `f`, `x`, `index`, `p`, `left`, `result`

These are cross-corpus universal noise from identifier streams
specifically — the right domain for slop. None of them overlap
with `lexical.hammers`'s banlist; treating them as noise will not
silence other rules.

## Layered design

The user's framework, validated by both papers above, separates
ignore lists by concern:

| Layer | Content | slop's policy |
|---|---|---|
| **1 — Universal noise** | Cross-corpus universal identifiers (Newman 14) + identifier glue words (`the`, `an`, `for`, `of`, ...) | Ship as `UNIVERSAL_NOISE` constant. Safe default for profile-style analyses. |
| **2 — SE boilerplate** | `manager`, `helper`, `service`, `util`, `handler`, `wrapper`, `factory`, ... | **Do not include.** This is `lexical.hammers`'s job. |
| **3 — Identifier glue** | English structure words inside identifiers — `to`, `from`, `with`, `by`, `of`, `and`, `or`, `in`, `on`, `for` | Folded into Layer 1. |
| **4 — Ecosystem idioms** | `ctx`, `err`, `req` (Go); `ptr`, `buf`, `len`, `idx` (C/C++); `props`, `state`, `ref`, `hook` (React); `self`, `cls`, `args`, `kwargs` (Python) | **Deferred.** Per-language layer; high-frequency but diagnostic *within* an ecosystem. See [backlog 09](../backlog/09.md). |
| **5 — Corpus-derived low-info** | TF-IDF / Poisson over a project's own identifier corpus | **Deferred.** Project-local; needs labelled fixture corpora to calibrate (Phase 06). |

The Lexicon does NOT apply any of these by default. Filtering is a
per-rule, per-query opt-in:

```python
modal = lex.modal_tokens(k=3, exclude=UNIVERSAL_NOISE)
alpha = lex.alphabet("prefix", exclude=UNIVERSAL_NOISE)
```

Rules that *count* tokens (e.g. `lexical.verbosity`, where the
prevalence of generic words IS the signal) pass no `exclude` — they
measure raw vocabulary.

## Other findings worth noting

Newman et al. also report:

- **~6K identifiers shared across 5+ of the 50 systems**, including
  `rotation`, `maxvalue`, `starty`, `getoffset`. The paper does
  not publish this list verbatim; it would need rebuilding from
  the source corpus if we ever want a wider Layer-1 floor.
- **A method-stereotype taxonomy** (their Table I, drawn from
  prior work — Dragoumi, Marinescu): `get`, `set`, `predicate`,
  `property`, `command`, `factory`, `controller`, `collaborator`,
  etc. These are the canonical "scaffolding verbs" the v2.0
  backlog discusses. When slop expands to handle scaffolding-
  verb noise, this taxonomy is the right citation.
- **A POS-style framework for source code** — `proper s-noun`,
  `s-noun`, `s-pronoun`, `s-adjective`, `s-verb` — derived from
  *declarations* rather than English meaning. Their tool runs on
  srcML over C/C++. slop does not adopt this: we have no consumer
  for per-identifier POS-style tags, and the framework requires
  type information beyond what tree-sitter routinely surfaces.

## Out of scope (upstream of filtering)

The literature on **identifier splitting** and **vocabulary
normalisation** (Binkley et al., Carvalho's *Lingua::IdSplitter*,
Lawrie/Hill's empirical splitting study) addresses problems
*upstream* of filtering: how to split CamelCase / snake_case
identifiers, how to expand abbreviations (`mgr` → `manager`,
`idx` → `index`), how to handle hard words. slop's
`split_identifier` already covers the splitting half; abbreviation
expansion is deferred. When a future rule needs to detect
"this codebase abbreviates inconsistently" or "the abbreviated form
is hiding a structural pattern," those papers become the
reference.

## Citations

> Newman, C. D., AlSuhaibani, R. S., Collard, M. L., & Maletic,
> J. I. (2017). "Lexical Categories for Source Code Identifiers."
> *24th IEEE International Conference on Software Analysis,
> Evolution and Reengineering (SANER 2017)*, Klagenfurt, Austria.
> pp. 228–237.
> <https://www.cs.kent.edu/~jmaletic/papers/SANER17.pdf>

> Fan, Y., Arora, C., & Treude, C. (2023). "Stop Words for
> Processing Software Engineering Documents: Do they Matter?"
> University of Melbourne & Monash University.
> <https://arxiv.org/abs/2303.10439>
> Online appendix: <https://zenodo.org/record/7865748>

The full bibliographic entries appear in [NOTICE](../../NOTICE)
under the lexical-rule citations.
