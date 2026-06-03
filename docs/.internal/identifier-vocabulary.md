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

## The distribution principle (Zipf 1949)

The Newman 14 list answers "what tokens are noise?" empirically.
Zipf's law answers "what *shape* should the rest of the
distribution have?" structurally.

In *Human Behavior and the Principle of Least Effort*, George Zipf
observed that the rank-frequency distribution of words in natural-
language corpora follows a power law: a word's frequency is
inversely proportional to its rank. The most common word appears
about twice as often as the second most common, three times as the
third, and so on. The general form is:

> `frequency(rank) ≈ C / rank^s`

with `s ≈ 1` for English. The defining shape is **heavy tail +
extreme head**: a tiny number of items account for most
occurrences; most items appear once or twice.

Subsequent work has shown software-identifier corpora follow the
same shape. Pierret & Poshyvanyk (ICPC 2009, *"An empirical
exploration of regularities in open-source software lexicons"*)
documented Zipf-shaped frequency distributions across Java
identifiers in 9 systems totaling 30M LOC; Newman et al. (SANER
2017, our seed paper above) observed the same on their 50-system
C/C++ corpus implicitly — their finding that only 14 identifiers
appear in *all* 50 systems is itself a Zipf consequence.

The v1.2.0 snapshot of slop confirms the shape on our own corpus
(see `docs/research/observations/05-diagnostic-suite-and-thresholds.md`):
177 of 475 distinct tokens (37%) appear exactly once, while a
single token (`node`) appears 144 times.

### Why this matters for slop

The Zipf shape gives us a structural reason to expect specific
parts of the distribution to be slop-laden vs. signal-rich:

- **Head (top ~5%, e.g. >32 occurrences in our snapshot)** — almost
  always infrastructure plumbing (`node`, `root`, `content`,
  `config`). High frequency *because* every component uses them,
  not because they're domain-meaningful. The hub-vs-packet design
  in `Lexicon.packets` already exploits this: max-normalised
  association naturally excludes hub tokens.
- **Body (middle ~25%, ~8–32 occurrences)** — where domain
  vocabulary tends to live. The actionable refactor signals
  (FindOptions cluster members, language-handler alphabets) sit
  here.
- **Long tail (bottom ~70%, ≤4 occurrences)** — mostly noise:
  one-off variable names, local helpers, hapax legomena. Useful
  as a vocabulary-richness metric but not as a sprawl signal.

This stratification is the empirical basis for our
`(min_bags=5, min_association=0.7)` threshold default — it places
the floor just above the long-tail noise.

## Tooling implications

Both sources are actively used, with room to expand:

- **Newman 14** ships as `UNIVERSAL_NOISE` in
  `slop.lexicon.affix` and is wired through every distribution
  method (`frequencies`, `modal_tokens`, `alphabet`, `coverage`,
  `overlap`, `packets`, `token_locations`, ...) via the
  `exclude=UNIVERSAL_NOISE` parameter. Observation 06 surfaced
  the need for a Layer-4 per-language idiom list (Python
  builtins) as a separate filter for body-identifier analysis;
  that list is the natural next addition.
- **Zipf** is not yet wired into the diagnostic primitives.
  Three concrete tooling uses, in order of effort:
  1. **Hapax-legomena ratio** (one number per corpus: fraction
     of tokens appearing exactly once) as a vocabulary-richness
     metric in `emit_diagnostic_report`. Trivial — already
     computable from existing data.
  2. **Zipf-residual signal** per token: actual frequency vs.
     expected frequency given the corpus's fitted Zipf
     distribution. Tokens with large positive residual at the
     head are hub-like; large positive residual elsewhere
     indicates over-represented domain vocabulary worth
     investigating.
  3. **Adaptive thresholds** for packets / sprawl: instead of
     hard-coded `min_bags=5`, derive the threshold from the
     corpus's Zipf elbow (the rank where head transitions to
     long tail). Self-calibrating across corpus sizes.

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

> Zipf, G. K. (1949). *Human Behavior and the Principle of Least
> Effort: An Introduction to Human Ecology*. Addison-Wesley,
> Cambridge, MA. The original observation; subsequent literature
> ("Zipf's law") refers back to this work.

> Pierret, D., & Poshyvanyk, D. (2009). "An empirical exploration
> of regularities in open-source software lexicons."
> *Proceedings of the IEEE 17th International Conference on
> Program Comprehension (ICPC 2009)*, Vancouver, BC. pp. 228–232.
> Documents Zipf-shaped frequency distributions across Java
> identifiers in 9 systems totaling 30M LOC.

The full bibliographic entries appear in [NOTICE](../../NOTICE)
under the lexical-rule citations.
