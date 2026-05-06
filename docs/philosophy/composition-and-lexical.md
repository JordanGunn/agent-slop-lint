# Composition and lexical methodology

The 1.1.0 release added two new rule suites — the
`composition.*` rules (`affix_polymorphism`,
`first_parameter_drift`) and an expanded `lexical.*` suite
(`name_verbosity`, `numbered_variants`, `weasel_words`,
`type_tag_suffixes`, `boilerplate_docstrings`,
`identifier_singletons`, plus the three-way `lexical.stutter` split).
This document records why those rules exist, what prior research
each one borrows from, and what was empirically tested before
shipping.

For full citations see [`references.md`](references.md).

## The agent-written-code pattern these rules target

Agent-extended codebases accumulate flat function families faster
than human-written code, because each prompt extension is a local
operation that doesn't see the whole file. Over a dozen edits, the
file develops a tabular structure (one helper per language, per
format, per backend) that a human author would have factored into a
class hierarchy, a dispatch table, or a polymorphic interface during
the second or third addition.

The flatness is invisible at any single edit. It only becomes
legible when you look across the file as a whole — and that's
exactly the analysis these rules perform. Each rule looks across a
collection of identifiers (function names, parameter names, local
bindings, docstrings) and surfaces patterns that suggest the missing
abstraction.

## composition.* — finding hidden classes from lexical signal

The two composition rules detect different forms of "the abstraction
is already implied by the names; it just hasn't been declared."

### `composition.affix_polymorphism`

**The signal:** clusters of identifiers sharing a stem with one
position varying over a closed alphabet. ``_python_extract``,
``_java_extract``, ``_csharp_extract`` is one such cluster: the
varying position holds a language name. When the same alphabet
appears across multiple operations, the cluster encodes a
``language × operation`` matrix — the canonical missing-namespace
pattern.

**The algorithm:** identifier-pattern detection from
Caprile & Tonella (2000), enriched with Formal Concept Analysis
(Wille 1982; Ganter & Wille 1999). FCA over the
binary entity × operation relation produces:

1. The maximal Formal Concepts — closed (entity-set,
   operation-set) pairs where every entity supports every
   operation. A concept with `n` entities and `k` operations is a
   candidate class with `k` methods and `n` instances.
2. The Hasse diagram of those concepts — the lattice of
   inheritance candidates. When entity A's operations strictly
   contain entity B's, A is a candidate child / specialisation of
   B (the rule reports this as an "inheritance pair").

**Prior art:** the Bavota et al. *Methodbook* line of research on
Move Method / Extract Class refactoring detection demonstrated that
co-occurrence and naming signal are reliable enough to recommend
class-extraction refactorings. This rule's signal is a more
focused variant: identifier-token overlap as a proxy for shared
semantic role.

**Filtering:** raw FCA produces a combinatorially large concept
lattice. Following the MDL principle (Rissanen 1978), only concepts
whose entity × operation product exceeds configured thresholds
(default `≥ 2 × ≥ 2`) are reported — small concepts have shorter
description as free functions than as a class.

### `composition.first_parameter_drift`

**The signal:** clusters of free functions sharing a first-parameter
name. When `n` functions all take `canvas` as their first argument,
the canvas is acting as a de facto receiver — the `n` functions
are de facto methods on a missing class.

**The algorithm:** a lighter-weight variant of the Bavota et al.
Extract Class line. Where Bavota's family of techniques uses
relational topic models over co-occurrence, this rule uses
first-parameter-name as a proxy for shared receiver-of-method.
Lower precision than relational-topic-model approaches, but
cheap enough to run on every lint pass; the signal is robust
because the convention "first parameter is the conceptual
receiver" predates Python's `self`.

**Verdict classification:** not every shared-first-parameter
cluster is a missing class. The rule classifies each cluster
into strong / weak / false-positive based on the parameter name
and any visible type. Only **strong** clusters generate
violations; the others appear in the summary so users can
review aggregate signal without failing the build.

## lexical.* — naming discipline and agent tells

The lexical suite measures vocabulary quality. Each rule targets a
distinct naming smell, with prior art that predates the rule by
decades:

| Rule | Prior art | What it tests |
|---|---|---|
| `lexical.verbosity` | Lawrie/Feild/Binkley 2006 | Mean tokens-per-identifier in a function body |
| `lexical.tersity` | Lawrie/Feild/Binkley 2006 | Fraction of cryptic ≤ 2-char identifiers |
| `lexical.name_verbosity` | Lawrie/Feild/Binkley 2006 | Tokens in a *function* / *class* name |
| `lexical.stutter.*` | Deissenboeck & Pizka 2006 | Identifiers repeating tokens from enclosing scope (split into namespaces / callers / identifiers) |
| `lexical.numbered_variants` | Harris 1955 (morpheme boundary) | Disambiguator suffixes (`_1`, `_v2`, `_old`, `_new`, `_local`, ...) |
| `lexical.weasel_words` | Deissenboeck & Pizka 2006 | Catchall vocabulary (`Manager`, `Helper`, `Util`, `Spec`, ...) |
| `lexical.type_tag_suffixes` | (slop original) | Identifier suffixes restating the annotation (`_dict: dict[...]`) |
| `lexical.boilerplate_docstrings` | (slop original) | Docstrings that just restate the function name |
| `lexical.identifier_singletons` | (slop original) | Functions where most named locals are write-once-read-once |

The "slop original" entries are not novel research — they are
specific, narrow operationalisations of the broader
"naming-discipline" line of research, targeted at agent tells that
were observed in practice but not previously published as
standalone metrics.

## Empirical grounding

The composition rules were not designed in a vacuum. Three rounds
of experiments — recorded in
[`docs/observations/composition/01.md`](../observations/composition/01.md)
and [`02.md`](../observations/composition/02.md), with seven
companion PoC scripts under `scripts/research/composition_poc/` —
evaluated five candidate algorithms across six sub-agent
invocations. The findings:

1. **Detection works.** Every candidate algorithm reliably surfaced
   the affix-polymorphism / first-parameter-drift patterns on
   slop's own kernel surface (which contains both, by design).
2. **Algorithm choice matters less than output format matters
   less than agent disposition.** Even when shown explicit
   inheritance candidates with full FCA enrichment, agents
   systematically prefer free-functions-with-data-tables over
   inheritance hierarchies.
3. **Therefore: the rule's job is to surface the option, not coerce
   the refactor.** The user always sees the rule output and can
   accept, reject, or adapt the suggestion. Coercing a specific
   refactor in the rule's output is both unhelpful (agents
   discount it anyway) and architecturally presumptuous (the
   alternative — a strategy table — is often the better choice).

This is why both composition rules ship with `severity = "warning"`
rather than `"error"`: they're advisory by construction.

## Why these rules and not others

The eight new rules were not selected to be exhaustive. They were
selected because:

- Each targets a distinct, observable pattern in agent-written code.
- Each has prior art in the software-engineering literature
  (composition rules: Wille, Caprile-Tonella, Bavota; lexical rules:
  Lawrie/Feild/Binkley, Deissenboeck-Pizka, Harris).
- Each is independently configurable, so users can dial down the
  rules they don't care about without losing the others.
- Each reports something concrete enough to act on (or to ignore
  with confidence). No rule reports "the code feels off."

If a candidate rule didn't have all four properties, it didn't
ship.

## What's deliberately not in the suite

- **Whole-file naming-consistency rules.** Cross-file identifier
  consistency is a real signal, but the right operationalisation
  depends on conventions that vary widely between codebases. The
  `weasel_words` configurable banlist is the closest in-scope rule;
  whole-codebase consistency is left to higher-level tools.
- **Per-language docstring conventions for non-Python languages.**
  `boilerplate_docstrings` is Python-only; JSDoc / Javadoc / Doxygen
  conventions differ enough that each needs its own rule. Deliberate
  follow-up.
- **Identifier-singleton detection in non-Python languages.** Python
  has the cleanest binding semantics for this rule; `let` / `var` /
  `const` in JS / TS / Rust / Java need per-language handling. Also
  a deliberate follow-up.
