# Codebase entity + views

Status: Codebase entity shape, auto-detect posture,
immutability, and slicing-on-views are locked. Record shapes,
the `scan()` signature, the view APIs, eager-vs-lazy
materialisation, and tree location remain open.

Companion docs: `language.md` covers the grammar interface
and concrete grammars that Codebase consumes; `linter.md`
covers the run loop that sits above Codebase.

## Scope of this document

What is settled:

- The Codebase entity shape: one `Codebase` per repo, scanning
  produces two derived views (`Structure`, `Lexicon`), rules
  depend on the views and not on `Codebase` directly.
- Language as a filter axis on the views, NOT an axis on
  `Codebase` itself (no "one Codebase per language" partitioning).
- Auto-detect is the primary mode. The grammar registry ships
  populated; `Codebase(root)` with no further config picks up
  every language fd finds. No "tell slop what to lint" step.
- `Codebase` is immutable post-scan. The scope is fixed by what
  was passed to the constructor; mutating-scope APIs are
  explicitly rejected.
- Slicing lives on the views (`Structure`, `Lexicon`), not on
  `Codebase`. Slice methods return *new view instances* over
  the same underlying parsed data; the parent is never mutated.
- **Views own metric computations.** Rules call view methods
  (`structure.cyclomatic(c)`, `lexicon.body_signature(c)`); they
  never walk AST nodes themselves. Records (`Scope`, `Callable`,
  `Occurrence`) stay pure-data identifiers; AST state lives
  inside the views, hidden behind the compute API.
- The record shapes themselves (`Scope`, `Callable`, `Occurrence`,
  `Parameter`, `Slop`, `ParseResult`) lock as pure-data carriers
  with no AST node fields (locked in
  ``src/cli/slop/corpus/records.py``).

What is NOT settled and is left for follow-up:

- The `Codebase.scan()` signature and what the parse-stream
  intermediate looks like (or whether it's an exposed type).
- The specific compute methods exposed by `Structure` and
  `Lexicon` (principle locked; surface enumerated as each rule
  ports — each port adds the method(s) its rule needs).
- The `Lexicon` slicing API specifics (`under()`, `where()`,
  `walk()` — principle locked, stub signatures landed; stress-
  test as rules port).
- Whether `Structure` and `Lexicon` are eager or lazy.
- Where the new code lives in the tree — locked as
  ``src/cli/slop/corpus/`` (no underscore prefix; v2.0 substrate
  is the public API surface).

---

## Locked: Codebase entity shape

`Codebase` is the corpus orchestrator. One `Codebase` per repo,
regardless of how many languages it contains. Scanning the
corpus produces two derived views; rules depend on whichever
view they need.

```
Codebase  ──scan()──▶  (parse stream)
                          │
                          ├──▶ Structure   (scopes, callables, deps, ...)
                          └──▶ Lexicon     (token bag, identifier records)
```

`Structure` is the substrate the structural rules consume
(scopes, callables, dependency edges, AST-derived metrics).
`Lexicon` is the substrate the lexical rules consume (the bag
of tokenised identifiers and the statistical queries over it).

### Principles

- **DIP at the rule boundary.** Structural rules depend on
  `Structure`. Lexical rules depend on `Lexicon`. Neither
  imports `Codebase` directly. Each view is the narrowest
  abstraction the rule needs.
- **ISP via two views, not one fat surface.** A lexical rule
  has no reason to see the AST tree shape; a structural rule
  has no reason to see the token bag. Splitting at the view
  layer keeps each rule's dependency surface minimal.
- **One walk, many views.** `Codebase.scan()` walks files once
  and parses each via the grammar; the parse output feeds both
  views. The economic argument for keeping `Codebase` as the
  orchestrator (instead of two parallel pipelines) is that the
  parse step is the expensive one.
- **Language is a filter, not an axis.** A repo is one codebase
  by every meaningful definition (one VCS root, one ownership
  story, one history). Language partitioning lives on the views
  (e.g. `lexicon.where(language=Python)`), not on `Codebase`.
  Per-language rules apply the filter; cross-language rules
  don't. This keeps the door open for cross-language signal
  (FFI boundaries, wrapper-vocabulary mimicry) without
  retrofitting the entity model.

---

## Locked: Codebase is immutable post-scan

Once `Codebase.scan()` has run, the corpus is fixed. There is
no `set_scope()` / `with_scope()` mutation API on `Codebase`
itself. Rationale:

- **Identity stability.** Callers holding a `Codebase`
  reference get the same answer every time. Mutating-scope
  APIs invite spooky action at a distance — whatever rule
  last mutated decides what the next caller sees.
- **It collapses two abstractions back into one.** Codebase
  IS the corpus. A *windowed view onto* the corpus is a
  different concern, owned by `Structure` and `Lexicon`. Push
  the window onto Codebase and you lose the distinction we
  spent design rounds establishing.
- **Concurrency stays open.** An immutable Codebase can be
  shared by parallel rules each producing their own slice;
  a mutable one forces serialization.

---

## Locked: Slicing belongs on the views

The "show me the lexicon under `src/cli/`" ergonomic the
caller wants is real and important. Its home is the view
slicing API, not Codebase mutation:

```python
codebase = Codebase(root)
codebase.scan()

# Default views span the full corpus
codebase.lexicon
codebase.structure

# Slicing produces NEW view objects; codebase unchanged
narrow = codebase.lexicon.under(path="src/").where(language="python")
narrow.frequencies()

# Different slice from the same Codebase, in parallel
docs_view = codebase.lexicon.under(path="docs/")
```

Each slice method returns a new view instance over the same
underlying parsed data. Cost is O(1) — the index is shared;
the view is a filter, not a copy of the underlying data. The
specific surface (`under()`, `where()`, `walk()`, etc.) is
still its own design round; the *principle* — slicing on
views, returning new views, parent immutable — is locked.

---

## Locked: Views own metric computations

Rules consume `Structure` and `Lexicon` through *compute*
methods, not by walking AST nodes themselves. The view is the
abstraction boundary; the AST is an implementation detail
hidden inside the view.

### Rule shape (locked)

```python
def run_cyclomatic(structure: Structure, rc: RuleConfig, config: SlopConfig):
    for c in structure.callables():
        ccx = structure.cyclomatic(c)        # view computes
        if ccx > rc.params["max"]:
            emit Slop(...)
```

The rule is **threshold-application + finding-emission**. It
contains no AST walking, no tree-sitter import, no
language-branching code.

### Why this is load-bearing

- **Records stay pure-data identifiers.** `Scope`, `Callable`,
  `Occurrence` carry qualname / kind / path / line / parent /
  parameters — they are *handles into the view's index*, not
  carriers of AST state. The deferred "AST on records?"
  question (round 1 of records) resolves to NO: records do not
  carry AST nodes. The view owns whatever AST data it needs.
- **One implementation per metric.** Java's `switch_expression`
  vs Python's `match` statement differ in how branches are
  counted. That difference lives in `Structure.cyclomatic`'s
  per-language path, ONCE. Every complexity rule
  (`cyclomatic`, `cognitive`, `npath`, `halstead`) sees the
  language-normalised metric, not the AST.
- **Memoisation is natural.** `structure.cyclomatic(c)` can
  cache per-callable; multiple rules reading the same metric
  share the computation. The old `_structural/ccx.py` design
  has no shared cache — every rule re-parses.
- **DIP/ISP holds at the rule boundary.** A rule depends on
  `Structure` (or `Lexicon`). It does not depend on
  tree-sitter, on the records module's internals, or on the
  Codebase. The view is the entire surface area the rule sees.

### Compute surface (enumerated as rules port)

Specific compute methods land as their first consumer ports.
The principle is locked; the method list grows incrementally.
Indicative surface based on the existing rules' needs:

```python
class Structure:
    # iteration / lookup (locked in stub)
    def scopes(self) -> Iterable[Scope]: ...
    def callables(self) -> Iterable[Callable]: ...
    def scope(self, qualname: str) -> Scope | None: ...
    def children(self, scope: str) -> Iterable[Callable]: ...

    # per-callable complexity metrics (land with their rule ports)
    def cyclomatic(self, c: Callable) -> int: ...
    def cognitive(self, c: Callable) -> int: ...
    def npath(self, c: Callable) -> int: ...
    def halstead_volume(self, c: Callable) -> float: ...
    def halstead_difficulty(self, c: Callable) -> float: ...

    # per-scope class metrics
    def class_coupling(self, scope: Scope) -> int: ...
    def inheritance_depth(self, scope: Scope) -> int: ...
    def inheritance_children(self, scope: Scope) -> int: ...

    # graph-level (deps, dead-code reachability, hotspots)
    def dependencies(self) -> DependencyGraph: ...
    # ...
```

```python
class Lexicon:
    # stats surface (locked in stub)
    def frequencies(self) -> Mapping[str, int]: ...
    def modal_tokens(self, *, top: int = 10) -> Sequence[tuple[str, int]]: ...
    def alphabet(self) -> AbstractSet[str]: ...
    def coverage(self, vocabulary: AbstractSet[str]) -> float: ...
    def overlap(self, other: Lexicon) -> float: ...

    # per-callable lexical computations (land with their rule ports)
    def body_signature(self, c: Callable) -> AbstractSet[str]: ...
    def body_overlap(self, c1: Callable, c2: Callable) -> float: ...
    def receiver_call_density(self, c: Callable) -> float: ...
    # ...
```

The list above is indicative, not exhaustive. The contract:
**every metric a rule needs lands as a method on its view; no
rule walks AST nodes directly.**

---

## Open — next rounds

### `Codebase.scan()` and parse-stream

The entity shape is settled (one Codebase, two views, one
walk). The API is not: `scan()` signature, what the parse
stream looks like, whether it's an exposed intermediate type
or an internal pipeline, whether `Structure` and `Lexicon` are
materialised eagerly during scan or lazily on first access.

### Eager vs. lazy materialisation

`Codebase.scan()` could materialise both views eagerly during
the walk, or hold the parse stream and compute views lazily
on first access. The plan leans eager (one walk, both views
populated, immediate); confirmed when the first rule port
lands and shows whether eager is fast enough.

### Compute-surface enumeration

The principle is locked: views own compute, rules consume.
The specific method list grows as each rule ports. Tracking
the cumulative surface (and noting any cross-rule helpers
that emerge) belongs in the rule-port intents, not as a
separate round.
