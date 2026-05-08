# Closed-alphabet entity recognition

**Status:** Active in v2 PoC battery; promotion to kernel pending.
Strongest standalone finding on slop's corpus.
**PoC:** [`scripts/research/composition_poc_v2/poc3_alphabet_entity.py`](../../../scripts/research/composition_poc_v2/poc3_alphabet_entity.py)

## Problem

When the same set of token values appears in many places — as keys
in module-level dicts, as positions in function names, as suffixes
in test files — the alphabet itself is functioning as an implicit
type. The codebase has, in effect, declared a `Language` enum or a
`Metric` set without ever introducing the corresponding type. The
duplication isn't of behavior; it's of the *concept the codebase
keeps re-deriving.*

The textbook example, from slop's own corpus:

- `_FUNCTION_NODES: dict[str, frozenset[str]]` keyed by language ID
- `_LANG_GLOBS: dict[str, list[str]]` keyed by language ID
- `_CLASS_NODES: dict[str, frozenset[str]]` keyed by language ID
- `_python_extract`, `_java_extract`, `_csharp_extract` etc. with
  language ID as a varying token position
- `tests/test_python_*.py`, `tests/test_java_*.py` files

The language alphabet `{python, java, javascript, c, cpp, ruby,
csharp, go, rust, julia, ...}` recurs in 9 distinct stems across 10
files with 36 module-level dict-key matches. No `Language` class
exists. The codebase has instead duplicated the implicit definition
in five separate dict declarations.

This pattern is not in the standard FCA / Extract Class literature.
The closest precedent is Tonella's aspect-mining work via FCA on
execution traces, but that method addresses cross-cutting *behavior*,
not cross-cutting *type identity*.

## Signal purpose

For each closed alphabet detected by affix-pattern analysis, this
method produces an **entity-ness score** combining:

1. **# distinct stems** the alphabet appears in (each varying
   position counts once)
2. **# distinct files** where alphabet members are referenced
3. **# module-level dict literals** whose keys overlap the alphabet
   by ≥ 2 members

Score = `2 × stems + files + 3 × dict_matches`

The weighting reflects observed signal strength. Dict-key matches
are the strongest indicator (a dict literal with language IDs as
keys is a near-explicit declaration that the codebase wants this
type). Stems are intermediate (multiple `_<lang>_*` patterns
indicate the codebase keeps re-implementing per-language behavior).
Files are weakest alone (an alphabet appearing in many files is
expected for any codebase-wide concept).

Reading the score:

| Score | Reading | Implication |
|---|---|---|
| > 100 | Codebase has an unwritten type definition | Strong refactor candidate. Introduce `class <AlphabetType>`; consolidate the duplicated dict definitions; replace `_<lang>_*` helpers with method dispatch or per-instance config. |
| 50-100 | Real cross-cutting concept; partial duplication | Worth surfacing; refactor depends on whether the alphabet has shared attributes beyond identity. |
| 10-50 | Recurring alphabet but not necessarily a missing type | Could be a domain enum; could be coincidental. Inspect manually. |
| < 10 | Local pattern, not codebase-wide | Suppress as noise (existing affix kernel already finds this case). |

## Algorithm

```
1. Run affix-pattern detection on the whole corpus (existing kernel).
2. For each cluster's closed alphabet A:
    n_stems = len(cluster.patterns)
    files = ⋃ {file for each (entity, file) in cluster.variants}
    n_files = len(files)

3. Walk every Python file's AST.
   For each module-level assignment statement whose RHS is a dict
   literal, extract the dict's keys:
        dict_keys = {keys of this dict literal}
   For each closed alphabet A:
        if |dict_keys ∩ A| >= 2:
            dict_matches[A] += 1

4. score(A) = 2 * n_stems + n_files + 3 * dict_matches
```

The dict-walk uses tree-sitter; module-level assignments in Python
are wrapped in `expression_statement` nodes whose `assignment` child
holds the actual `left = right` pair. Keys can be strings or
identifiers; both are normalized to lowercase for matching.

## Citations

- **Wille, R. (1982).** "Restructuring lattice theory: an approach
  based on hierarchies of concepts." *Ordered Sets*, NATO Advanced
  Study Institutes Series 83, 445-470.
  The foundational FCA paper. The closed-alphabet detection used
  here is downstream of Wille's binary entity-attribute relation
  framework — the alphabet IS an FCA extent — but the *scoring*
  for "entity-ness" is not from Wille.

- **Ganter, B. & Wille, R. (1999).** *Formal Concept Analysis:
  Mathematical Foundations.* Springer.
  Canonical FCA reference book.

- **Tonella, P. & Ceccato, M. (2003).** "Aspect Mining through the
  Formal Concept Analysis of Execution Traces." *Proceedings of
  the 11th IEEE Working Conference on Reverse Engineering.*
  Closest published precedent for using FCA to find cross-cutting
  concerns in code. They use execution traces as the data source;
  we use static co-occurrence of identifier tokens. The framework
  ("FCA reveals latent concepts the codebase didn't declare") is
  the same.

- **Caprile & Tonella (2000)** — for the affix-pattern step that
  produces the alphabets in the first place.

## Modifications

This method is largely **novel**, and we flag that explicitly. The
modifications from the closest published methods:

- **Subject of FCA: alphabets, not entities.** Wille's FCA studies
  what *operations* an entity has. We invert this: given a closed
  alphabet, we ask what makes the alphabet itself entity-worthy.
  This isn't standard FCA — it's a pre-FCA scoring step that
  decides whether the alphabet deserves to be modeled at all.
- **Dict-literal corroboration.** The "dict-key matches" component
  of the score is not in any cited paper. The motivation is
  empirical: when a codebase has multiple module-level dicts with
  the same keys, that's a near-explicit declaration of a missing
  type, and weighting that signal heavily produces the right
  ranking on slop's corpus (Language alphabet beats every other
  by a wide margin).
- **Score weights are heuristic.** We have no theoretical
  justification for `2 × stems + files + 3 × dict_matches` — the
  weights were chosen so that on slop's corpus, the language
  alphabet wins clearly. Cross-corpus calibration is a deliberate
  next step.

## ELI5

Some sets of words in a codebase show up everywhere:

```python
_FUNCTION_NODES = {"python": ..., "java": ..., "ruby": ...}
_LANG_GLOBS    = {"python": ..., "java": ..., "ruby": ...}
def _python_extract(...)
def _java_extract(...)
def _ruby_extract(...)
```

The set `{python, java, ruby, ...}` is showing up in three different
guises: as keys of a config dict, as keys of another config dict,
and as a varying token position in helper function names. The
codebase keeps re-deriving the fact that "we support these
languages."

The claim of this method: when you see the same set of words
recurring across multiple unrelated structural positions in the
code, *those words probably want to be a type*. There should be a
`class Language` somewhere whose instances are these languages,
with attributes (`name`, `file_extensions`, etc.) that the various
dicts are currently storing scattered.

The score is built to reward exactly this:

- **Many stems use the alphabet** → 2 points each. The codebase has
  many "X varies by language" code paths.
- **Many files reference alphabet members** → 1 point each.
  Background spread.
- **Module-level dicts have alphabet members as keys** → 3 points
  each. This is the smoking gun: the codebase already implicitly
  defines the type, just as a dict.

A high score means: the codebase has an unwritten type. An agent
reading the report can introduce that type as a `class`,
consolidate the duplicated dicts as instance attributes, and
replace the per-language helpers with methods or strategy-table
lookups.

A low score means: this alphabet recurs but doesn't have the
recurrence-density of a real type. Probably just a domain term that
shows up in a few places. Don't refactor.
