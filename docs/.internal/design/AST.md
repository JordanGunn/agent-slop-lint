# Component Model Design

Status: proposed design. Interfaces first; no implementation until the ABC spine
is agreed and validated against the hardest existing rules.

This document defines an explicit component model for a codebase so that
scoping, lexicons, structural metrics, dependency analysis, and call analysis
all have stable semantic targets.

## Framing: rebuild, not retrofit

The current implementation (`Tree`, `Structure`, `Lexicon`, view-bound rules)
proved the thesis: academic metrics (McCabe, Campbell, Chidamber-Kemerer,
Martin, Halstead, Tornhill) computed over real code surface real structural
debt, and an agent can act on them. That experiment succeeded. But the code is
a provenance mixture — pieces from different time periods and visions, with no
single model of what a codebase *is* before metrics are projected over it. The
recurring symptom is that "scope" means six different things, and every rule
re-decides what it targets.

The decision is to build the model properly, as if from scratch.

**The old codebase is an inventory, not a template.** It is the authoritative
list of *what we want to compute* — every metric, every rule, every language
adapter is a known-good requirement. It is *not* a blueprint for *how the new
entities should be shaped*. We must avoid provenance collapse: do not bend a new
entity to accommodate an old data structure. Design each entity from the model
down; consult the old code only to confirm "yes, we still want to compute this,"
then express that computation at its correct altitude in the new model.

## Problem

The word "scope" currently carries too much meaning. It can mean:

- a filesystem boundary
- a language syntax boundary
- a rule emission unit
- a lexical analysis window
- a structural metric aggregation target
- an import or build-system namespace

Those are related, but they are not the same thing. When the model does not
name them separately, design details keep reintroducing ambiguity, and metrics
get applied at the wrong altitude (CK metrics asked of a module, package metrics
asked of a function).

The fix is to name the component entities first, give each a stable identity,
and make lexicons, structural metrics, dependency graphs, and call graphs
*projections over those entities*.

## Core Hierarchy

```text
Corpus
  -> Realm
    -> Package
      -> Module
        -> Class
          -> Callable
```

This describes ownership. It does not imply that every language maps to the
filesystem the same way; adapters carve the entities from source.

The leaf is `Callable` (function/method), not `Class`. This matters: the
primitive structural metrics (cyclomatic, cognitive, npath, halstead) are
*defined on a callable* and nowhere else. Everything above the callable
aggregates by composition — see "Metric Altitude."

## Container Taxonomy

```text
Component        = the ABC base for every node (identity, extent, projections)
AggregateContainer = Corpus | Realm | Package      (own components)
SymbolContainer    = Module | Class | Callable       (own declarations)
```

Naming note: the base is `Component`, not `Scope` — `tree/records.py` already
binds `Scope` as a parse record and `linter/tags.py` as an enum. The model must
not reuse the overloaded word it exists to disambiguate.

- **AggregateContainers** own other components and derive every projection
  upward from their children. They own no declarations directly.
- **SymbolContainers** own declarations directly (callables, variables,
  properties, nested types). Rules that need declaration ownership target a
  SymbolContainer kind, never an arbitrary scope string.

## Metric Altitude and Aggregation

This is the principle that resolves the original pain. **Every metric has
exactly one home altitude where it is *defined*. Higher altitudes do not
redefine it — they aggregate it.**

- `cyclomatic`, `cognitive`, `npath`, `halstead` are defined on **Callable**.
- A **Class** does not have "a cyclomatic complexity" of its own; it has WMC —
  the aggregate of its methods' complexities (this is literally the
  Chidamber-Kemerer definition). CK metrics (WMC, DIT, NOC, CBO, LCOM) are
  defined at the **Class** altitude and require a class to exist.
- A **Module** aggregates its functions' and classes' metrics; it adds
  module-altitude facts (fan-in/out, god-module size).
- **Package** is where Martin's package metrics live (rigidity / instability /
  uselessness / abstractness). They are *undefined* below a package.
- **Realm** and **Corpus** are aggregate-only: their projections are the union
  of their children's. Realm additionally owns the language/sdk resolver.

So "polymorphic cyclomatic across module and class" is not method overriding —
it is the same recursive aggregation applied at each altitude. A node never
claims a metric undefined for its kind. This is what makes the rule-targeting
table stop being ad hoc.

## Interface Spine (ABC strawman)

```text
Component (ABC)
    KIND       : ClassVar[ComponentKind]
    id         -> ComponentId           # (kind, qualname, extent spans): stable, hashable
    name       -> str                   # local simple name
    owner      -> Component | None
    extent     -> Extent                # files / byte-spans / ast roots
    files      -> tuple[Path, ...]      # distinct files spanned (1 for py module, N for go)
    children() -> Sequence[Component]
    ast()      -> AST                   # parsed syntax over THIS extent (lazy, sliced)
    lexicon()  -> Lexicon               # token-space derived from ast() (lazy, sliced)

  AggregateContainer(Component)         # projections are aggregates of children
      Corpus    : root; config; scan(root,config); realms()
      Realm     : grammar/paradigm; root; packages()        # language/sdk lives here
      Package   : path; packages(); modules()               # + classes()/functions() are
                                                             #   paradigm-gated convenience

  SymbolContainer(Component)            # owns declarations directly: symbols()
      Module    : imports()                                  # functions/classes paradigm-gated
      Class     : is_abstract; methods(); properties(); bases(); nested  # CK metrics defined here
      Callable  : kind; parameters(); locals(); nested()     # primitive metrics defined here
```

Two settled decisions:

1. **Projection lives on the component.** `module.lexicon()`, `class.ast()` are
   lazily computed per component. There is one `AST` type and one `Lexicon`
   type, each *bound to an extent* — never per-kind subclasses. `AST` is the
   parsed syntax (a subtree for a Callable, a forest for an aggregate); `Lexicon`
   derives from it (flatten → tokenize → split → strip noise) unioned with the
   component names in the extent. Both are lazy and *sliced from the owner's
   parse* (a child reuses the parent, never re-parses); pure functions of
   (extent, parse) keyed by `ComponentId`, so caching can be added later without
   redesign. Scope becomes component identity, not an external string.
2. **Identity is a stable key, not object identity.** `ComponentId` is
   `(kind, qualname, extent-byte-spans)`. tree-sitter node identity is not
   stable across accesses, and the derived graphs must reference nodes durably.

## Entity Properties & Ownership

Properties and class constants are fixed up front (not discovered missing
mid-build). Cross-cutting state has one owner each.

```text
Component (all)  KIND  id  name  qualname  owner  extent  files  ast()  lexicon()  + complexity
Corpus           root: Path   config: AnalysisConfig   scan(root, config) classmethod factory
Realm            root: Path   grammar: type[Grammar]   paradigm (derived)   language
Package          path: Path
Module           imports: Sequence[ImportDecl]    (declarations via symbols())
Class            is_abstract: bool   methods / properties / bases / nested_classes
Callable         kind: CallableKind   parameters / locals / nested
```

Ownership decisions:

- **Config → Corpus.** The analysis boundary owns the config; children read it
  through the owner chain, never carry copies.
- **Grammar → Realm.** The Realm is the layer that owns grammars; it holds
  one paradigm-typed `Grammar` adapter (the ported `slop.language` hierarchy).
  `Realm.paradigm` is derived from the grammar, not independently set.
- **Source-root detection → Corpus.scan.** A classmethod factory that detects
  language source roots and constructs one Realm per resolver world; detection
  internals are private. Polyglot roots yield multiple Libraries.
- **KIND is a class constant**, so identity/dispatch/filtering key on a constant
  rather than runtime type checks.

### Avoiding the legacy's over-control

Reference the old arch, but note where it spent excessive effort steering
behaviour and design that out:

- **`post_scan_adjust`** rewrote mis-parented records (Go receiver methods, Rust
  `impl` methods) *after* a generic walk. Adapter-driven carving should parent
  correctly by construction — the fixup hook should not exist.
- **~20 control-flow knobs on `Language`** (`decision_nodes`, `compensating_decisions`,
  `bare_else_keyword`, `body_skip_types`, …) exist to steer one central complexity
  walker across languages. Consider letting the grammar own its complexity walk
  so the knowledge lives where the metric is computed, instead of exporting a
  large control surface to a shared algorithm.

## Interface Segregation (capability, not universal methods)

Not every container can answer every question. A Go package and a C translation
unit have no classes; CK metrics are undefined there. `classes()` and the CK
metric surface are therefore **capabilities** a container *may* expose, mirroring
the existing paradigm hierarchy (ObjectOriented / Procedural / MultiPurpose) —
not universal methods that return `[]` for half the languages. "Undefined here"
must be honestly absent, not silently empty. A rule asking for a capability a
component lacks is a targeting error the model can surface, not a quiet no-op.

## AST, Symbol Tree, and Extent

Every component exposes three distinct concepts.

- **Extent** — the source material a component owns: files, source ranges, AST
  roots, declarations. A Python Module's extent is one file; a Go Module's is
  all files in a directory sharing a `package` declaration; a Class's may be
  several ranges in languages with partial/reopened classes.
- **AST** — syntax. The parsed tree(s) over a component's extent. *Rules* do not
  consume AST nodes directly (they consume metrics); but the AST is itself a
  first-class, tree-sitter-isolated subsystem that metrics walk — see *AST
  Subsystem*.
- **Symbol Tree** — normalized semantic ownership: what declarations exist, who
  owns each, name/kind/location/containing-component. It is built *from* AST by
  language adapters; it is not the AST.

## Per-Entity Projections

For any component `C`:

- `lexicon(C)` — identifier vocabulary inside `C`
- `ast(C)` — parsed syntax over `C`'s extent (structural metrics are walked from it)
- `symbols(C)` — declarations `C` owns
- `dependencies(C)` — dependency edges owned by / incident to `C`
- `calls(C)` — call edges owned by / incident to `C`

A package lexicon is derived from its modules and classes; a class lexicon from
its methods, properties, and child types; a callable lexicon from its own
identifiers. Aggregation is composition over the base case directly below.

## Language Adapter Responsibilities

The component hierarchy is an ABC tree (OOP). Per-language *carving* —
what counts as a Realm / Package / Module / Class / Callable in each language
— is adapter-driven, never `if lang == ...` branching inside the hierarchy. The
`Realm` owns the adapter (it already holds the grammar). This keeps two
concerns apart: the hierarchy is polymorphic by entity kind; language specifics
are tabular dispatch on the adapter.

**The adapter is the legacy `slop.language` hierarchy, ported as-is** — it is a
directly-reusable inventory item, not something to redesign:

```text
Language (ABC)                 -- tabular tree-sitter contract (~40 classmethods)
  Procedural(Language)         -- functions()                  (free functions)
  ObjectOriented(Language)     -- classes() [abstract here only], methods()
  MultiPurpose(OO, Procedural) -- both (diamond marker)
```

This already solves paradigm capability the right way (ISP: `classes()` abstract
on `ObjectOriented` only) and already accommodates non-inheriting languages
(`extract_superclasses()` → `[]`, so Rust/Go contribute 0 to DIT/NOC). The
**grammar paradigm decides which typed accessors a carved Module/Package
exposes** — a Procedural realm's Modules expose `functions()`/`constants()`
and no `classes()`; an ObjectOriented realm's the reverse; MultiPurpose both.
So the component model must NOT invent a parallel capability vocabulary; it
derives capability from the Realm's grammar paradigm.

Each adapter answers:

- What constitutes a Realm / Package / Module / Class / Callable?
- Which declarations belong directly to Modules vs Classes?
- How are imports resolved into dependency edges?
- How are calls resolved into call edges?

```text
Python  Realm: configured source root   Package: directory   Module: .py file        Class: class stmt
Go      Realm: Go module                Package: import dir   Module: dir's pkg files Class: none (receiver types map partially)
Rust    Realm: crate                    Package: mod segment  Module: mod unit        Class: struct/enum/trait/impl
Java    Realm: source set/build target  Package: namespace    Module: compilation unit Class: class/iface/record/enum
C/C++   Realm: configured root/target   Package: ns/dir/group Module: TU/header group Class: class/struct where semantics allow
```

C/C++ require explicit humility: without build-system knowledge some boundaries
are best-effort. The model carries confidence and unresolved boundaries rather
than forcing false precision.

## AST Subsystem — first-class, tree-sitter-isolated

The current `model/ast.py` is not an AST; it is a thin fragment built only to feed
the component model. The actual AST *functionality* has no owner — it is sprawled
across `parse.py`, `grammar/`, `model/ast.py`, and a single traversal vocabulary
copy-pasted into ~12 metric modules. By slop's own thesis, that sprawl is the
fingerprint of slop, not a design to preserve. This subsystem gives the AST one
owner.

### Principle

`ast/` is **strictly the AST**: a language-agnostic, pythonic *proxy over
tree-sitter*. It parses, walks, queries, and renders syntax — and nothing else in
slop touches a raw tree-sitter node. We lean on tree-sitter at full power (queries,
cursors, fields) and isolate it behind the package boundary. `ast/` imports nothing
from above it (no `component`, no metric, no linter). You can point it at source,
get a walkable/renderable tree, and inspect it with zero knowledge of components or
metrics — that standalone-ness is a requirement (it powers the AST visualizer), not
a nicety.

### Layering (the AST is the lowest layer)

```text
ast/         pure syntax — a proxy over tree-sitter
   ↑ consumed by
component/   semantic code shape (Corpus..Callable), carved from AST + filesystem
   ↑ consumed by
linter/      rules, config, dispatch, findings
```

The only thing crossing *downward* into `ast/` is `Span` — a pure source-location
primitive `(path, start_byte, end_byte)`. It lives in `ast/`; the component layer
imports it for identity. `component → ast` is already the established direction
(`aggregate.py` imports `Grammar`/`Paradigm`); a naive relocation of the AST that
kept its `component.identity` import would instead create a `component ⇄ ast`
cycle. Moving `Span` down is what keeps the edge one-directional.

### Package layout

```text
ast/
  grammar/    the 11 concrete grammars — translate raw nodes → facts.
              These legitimately touch raw tree-sitter nodes; they are the
              translation layer and live correctly inside ast/.
  paradigm/   Grammar ABC + Procedural/ObjectOriented/MultiPurpose tiers
  parse.py    (moved from top level) load grammar + parse a file → ts.Tree
  span.py     Span (moved from component/identity.py)
  nodes.py    NodeKind — neutral, language-agnostic node categories
  tree.py     AST + Node — the proxy (the ONLY non-grammar holder of a ts node)
```

### The proxy API (derived from what the consumers actually re-implement)

```python
# ast/tree.py
class Node:
    """A pythonic proxy over one tree-sitter node — the only way the rest of
    slop reads syntax. Identity is the span, never id(node)."""
    @property
    def kind(self) -> NodeKind: ...        # neutral category, via the grammar
    @property
    def type(self) -> str: ...             # raw ts type — escape hatch for the long tail
    @property
    def span(self) -> Span: ...            # durable identity
    @property
    def text(self) -> str: ...             # sliced from content on demand
    @property
    def named(self) -> bool: ...           # ts is_named
    @property
    def parent(self) -> "Node | None": ...
    def children(self) -> tuple["Node", ...]: ...
    def field(self, name: str) -> "Node | None": ...   # child_by_field_name, wrapped
    def body(self) -> "Node": ...          # grammar-driven unwrap→body (was resolve_body)
    def walk(self, prune: frozenset[NodeKind] = frozenset()) -> Iterator["Node"]:
        ...                                # DFS; stop descent at prune kinds (the
                                           # "don't cross nested callables" need)
    def query(self, pattern: str) -> tuple["Node", ...]: ...  # full ts query power, wrapped
    def render(self, indent: int = 0) -> str: ...   # ascii tree from THIS node down
    def to_dict(self) -> dict: ...         # serialization (json/yaml dump)

class AST:
    """One parsed file. Owns the ts.Tree (keeps it alive so node refs stay valid),
    the source bytes, the path, and the grammar. Hands out Node proxies."""
    @property
    def root(self) -> Node: ...
    def at(self, span: Span) -> "Node | None": ...   # smallest node covering span (was _descend_to_span)
    def render(self) -> str: ...
```

`AST` is **per file**. A component whose extent spans several files (a Go Module,
a reopened class) is the *component layer's* composition over multiple `AST`s —
aggregation is composition over the base case, consistent with the projections
model. `ast/` does not model forests.

**Invariant rules** (both from bug classes already hit here):
- `Node.__eq__`/`__hash__` key on `span`, never `id(node)` — tree-sitter node
  identity is not stable across accesses.
- `AST` holds the `tree_sitter.Tree` for its lifetime so held node references stay
  valid.

### NodeKind — the language-agnostic vocabulary

A small neutral enum for the cross-language constructs the AST commits to:
`CALLABLE, CLASS, BRANCH, LOOP, SWITCH, CASE, TRY, CATCH, CALL, IDENTIFIER,
LITERAL, BOOLEAN_OP, IMPORT, PARAMETER, OTHER`. The raw→neutral mapping is the
grammar's *existing* vocabulary methods (`decision_nodes()`, `loop_nodes()`,
`callable()`, …) — no new table, the grammar already categorizes types. Raw
`.type` is retained as the escape hatch for the long tail. (This revives a real
inventory item: the legacy `slop.language.ast` per-category node enums.)

### The boundary: AST owns navigation, metrics own math

The investigation (heatmap below) showed `complexity.py` tangles two different
things. Keep them apart:

- **Folds into `ast/`** — generic navigation: DFS, child/field access, text decode,
  byte-span arithmetic, type-set filtering, tree-sitter queries, body unwrap. This
  is the vocabulary duplicated across 7–11 files.
- **Stays as compute** — *structure-directed* algorithms whose control flow IS the
  algorithm: NPath (`_npath_of_if/switch/try`, ~130 lines — the path formula
  differs per syntactic role and does not collapse to a generic walk) and cognitive
  scoring (nesting penalty + compensation + boolean-chain continuation). These
  re-express against the Node API and shed their hand-rolled plumbing; they do
  **not** move into `ast/`.

Hard line: **do not let the AST absorb metric math.** That would rebuild the v2 sin
(substrate owning algorithm/policy) inside `ast/`. `complexity.py` shrinks and
re-expresses; it does not vanish.

### Evidence — the duplication heatmap (model/ consumers)

One traversal vocabulary, copy-pasted. Files in `model/` exhibiting each idiom:

```text
DFS stack-walk         7    child_by_field_name   4
.children iteration   11    tree-sitter query      2   (imports.py, annotations.py)
text .decode()         8    node.type in/== filter 6   (21 of them in complexity.py)
byte-span arithmetic   9
```

`complexity.py` is the epicenter (6 walks, 15 children-iters, 21 type-filters).
`components.py` (0 idioms — pure orchestration) and `hotspots.py` (git + aggregate)
are NOT duplication and are untouched.

### Pruning targets (what dissolves)

- **Delete** `model/ast.py` (`Root`, `AST`, `_descend_to_span`) — superseded by
  `ast/tree.py`.
- **Move** `parse.py` → `ast/parse.py`; **move** `Span` out of
  `component/identity.py` → `ast/span.py`. `component/identity.py` re-exports
  `Span` (`from ..ast.span import Span`) so the ~6 existing
  `from ..component.identity import Span` sites do not change. `Extent` and
  `ComponentId` stay in `component/`.
- **Per consumer**, delete the hand-rolled traversal and re-express on `Node`:
  - `complexity.py`: delete `_unwrap_definition`, `resolve_body`, `_bool_op_text`,
    and all raw `stack`/`.children`/`child_by_field_name`/`.decode`/`.type in`
    mechanics. Keep `_count_decisions` (→ a few lines), `_cognitive_walk` scoring,
    the NPath family. `halstead.py` swaps its `resolve_body` import for `node.body()`.
  - `relational.py`: delete `_body_of` + the DFS in `callees_of`/leaf collection;
    keep the Jaccard/fingerprint/island compute.
  - `callable_measures.py`, `class_index.py`, `orphans.py`, `lexicon.py`,
    `dependency.py`: delete DFS/decode/field plumbing; keep compute.
  - `imports.py`, `annotations.py`: route their tree-sitter queries through
    `Node.query()`; drop the direct `tree_sitter` import.
  - `carve.py`: re-express definition-finding on `Node` (kind/field) — stays in the
    component layer, gets simpler.
- **Do NOT prune** `ast/grammar/*` raw-node usage — it is the translation layer,
  correctly inside `ast/`.

`AST.slice(extent)` on the projection protocol becomes span-based (`at(span)` /
spans) — it currently has **zero callers**, so the signature change is free.

### New code (what gets built)

- `ast/span.py` — `Span`.
- `ast/nodes.py` — `NodeKind`.
- `ast/tree.py` — `AST` + `Node` proxy (API above).
- `component/identity.py` — re-export `Span` from `ast/`.
- `component/projection.py` — align the `AST`/`Lexicon` protocol `slice` to spans.

### Migration path (proxy first, prove, then attrition)

1. Build `span.py`, `nodes.py`, `tree.py`; move `parse.py` in; wire the `Span`
   re-export. `ast/` now self-contained.
2. **Prove on cyclomatic** — the cleanest consumer (post-fold ~5 lines). Port it
   onto the Node API and oracle-check identical across all 11 grammars.
   `tests/test_multilang.py` already asserts per-language cyclomatic values — it is
   the built-in oracle.
3. **Attrition** — migrate remaining consumers family by family, each
   oracle-checked against current measurements. Delete `model/ast.py` once nothing
   imports it.
4. **Done** = a grep shows zero raw-node access (`.children`/`.type`/`start_byte`/
   `child_by_field_name`) outside `ast/grammar/` and `ast/tree.py`. Until then,
   tree-sitter leakage persists by design of the staged path — "isolated" is the
   target reached by attrition, not on day one.

**Status: complete** (commits `307cda3`..`e138942`). The proxy was proven on
cyclomatic (oracle: `test_multilang`), then every consumer migrated by
attrition — cognitive/combinatorial/halstead, imports/annotations (via
`Node.query`), relational/magic_literals/CK-coupling, `build_lexicon`, and
`carve` — each oracle-checked against the full suite (63/63). `model/ast.py` is
deleted and the dead `component.ast()` projection retired (the AST is the proxy;
`Lexicon` stays the per-component projection). Residual raw-node access lives
only in the grammar adapter layer (`ast/grammar/` + the `Grammar` ABC's default
extractors in `ast/paradigm/base.py`) and `ast/tree.py`; `model/` reaches raw
solely via `Node.raw` handoffs to grammar extractors. Two follow-ups noted below.

**Follow-ups (not blocking):**
- *stdlib shadow:* on Python 3.14, `from dataclasses import dataclass` internally
  does `import ast`, so running Python with `src/slop/` as CWD resolves `ast` to
  the local package and circular-crashes. Installed/`uv`/pytest paths are fine
  (absolute `slop.ast`); it only bites a bare interpreter launched inside
  `src/slop/`. Revisit if it proves a real footgun (rename `ast/`→`tree/`, or a
  sitecustomize guard).
- *NodeKind coverage:* `IMPORT`/`PARAMETER` map through `OTHER` (no single-type
  grammar set); wire them if a consumer needs the neutral kind.

## Build Plan

Interfaces before implementation. No business logic until the spine is agreed.

1. **Define the Component spine** — `Component` ABC, `AggregateContainer` /
   `SymbolContainer`, the six concrete kinds, `ComponentId`, `Extent`, and the
   capability interfaces (OO classes/CK). ABCs and signatures only; no bodies.
2. **Validate against the hard rules** — prove the spine expresses, on paper,
   the three rules that confuse us most today: class WMC (the all-classes-vs-one
   question), Martin package rigidity/uselessness, and confusion's island
   question. If any needs a scope string, the spine is wrong.
3. **Build the ComponentIndex** — carve `Corpus -> ... -> Callable` from
   parse results. Conservative and language-limited first (Python-shaped),
   establishing identity and ownership before chasing every language edge case.
4. **Build the projections** — the `AST` proxy (see *AST Subsystem*: a
   tree-sitter-isolated `Node`/`AST` in `ast/`, built proxy-first then proven on
   cyclomatic and migrated by attrition) and one `Lexicon` type (token-space
   derived from the AST), each lazily instantiated and sliced per component over
   its extent.
5. **Port rules by family, old code as inventory** — module/package rules,
   then class/complexity, then lexical over SymbolContainers. For each rule,
   read the old implementation only to confirm the computation we want, then
   re-express it at its home altitude. Do not import old shapes.
6. **DependencyGraph**, then reconsider **CallGraph** against the bar above.

## Open Questions

- **Realm name (resolved).** Named `Realm` — "one language/sdk resolver world,
  the source-code root of a homogeneous-language application component." Chosen
  over `Library` (implied an installable artifact, collided with Go's
  `module -> package`), `Target` (collided with the rule-targeting model),
  `Source` (collided with `extent.sources`/`files`), and `Buildable` (an
  adjective-as-noun that asserted a build step the model deliberately doesn't
  require).
- **Package/Module collapse.** Where they share extent (Go), the adapter emits
  paired entities with shared extent; they stay conceptually distinct (Package =
  namespace, Module = symbol container).
- **Build-system awareness.** The model works without it but allows confidence
  levels and unresolved boundaries rather than false precision.
- **Non-class symbol containers.** Languages without classes may have
  struct/trait/impl/receiver-bound types that map *partially* to Class for
  metrics. Adapters must not invent Class entities the language semantics don't
  support.

## Summary

Separate ownership, syntax, vocabulary, metrics, and graphs.

```text
Ownership:   Corpus -> Realm -> Package -> Module -> Class -> Callable
Taxonomy:    AggregateContainer = Corpus|Realm|Package ; SymbolContainer = Module|Class|Callable
Projections: ast / lexicon / symbols / dependencies / calls, per component (lazy, sliced)
Principle:   each metric defined at one altitude, aggregated upward; nothing claims a metric it lacks
Identity:    stable ComponentId, never object identity
Build:       interfaces first, validate against hard rules, port old computations as inventory
```
