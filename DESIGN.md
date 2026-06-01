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
- **AST** — syntax. The parsed tree(s) over a component's extent. AST stays an
  implementation detail of parse results and views; rules do not consume AST
  nodes directly.
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

## Rule Targeting Model (validation centerpiece)

Each rule declares the entity kind it targets, and each metric resolves to
exactly one home altitude. This table is how we validate the interface: if every
existing rule maps cleanly onto a kind without inventing scope strings, the spine
holds.

```text
complexity.cyclomatic / cognitive / npath / volume   -> Callable (aggregated upward; summed at every container)
WMC                                                   -> NOT a metric: weighting family. weight=cyclomatic => class.cyclomatic(); weight=1 => method_count()
god_module                                            -> Module
ck.* (dit, noc, cbo, lcom, nom)                       -> Class        (OO capability)
rigidity / instability / uselessness / abstractness   -> Package
deps / cycles                                         -> DependencyGraph
hotspots                                              -> Corpus/Module (+ git churn)
redundancy / clones                                   -> Module
call-islands (legacy "confusion", structural)         -> Module
lexical concept-dispersion (the user's "confusion")   -> any-altitude lexicon (hapax residual vs Zipf baseline, maturity-gated)
stutter / imposters / slackers / sprawl               -> SymbolContainer / Package lexicon
vocabulary                                            -> any-altitude lexicon (Realm/Package/Module/Class)
```

Rule output may still expose a string `scope` for human and machine consumers,
but internally the target is an entity kind with identity.

## Finding Ontology

A finding has two **orthogonal** axes. Collapsing them (the legacy mistake) loses
the most-used cell — the prescriptive-but-non-gating warning.

**Disposition (epistemic — what slop claims):**

- **Verdict** — a defect reverse-engineered from sloppy code: the action is agreed
  and the fix is prescribable deterministically. Carries a `prescription`.
- **Observation** — a claim-free empirical nudge ("look here; this may be a symptom
  of something larger"). Carries `evidence`, no prescription. Used where a
  measurement is informative but no remedy can be honestly prescribed (e.g. the
  token distribution is a Zipf near-invariant, so no scalar threshold is honest). An
  observation makes no precision claim, so it *cannot* be a false positive.

**Severity (operational — what it does to the build):** `error` (exit 1) > `warning`
(advisory) > `info` > `off`. A separate dimension layered on disposition.

**Coherence invariants (enforced by type, not runtime-validated):**

- Observation ⟹ severity `info`, action `INVESTIGATE`, no prescription, carries
  evidence. (A build failure is itself a precision claim; an observation makes none,
  so it cannot gate.)
- Verdict ⟹ severity `warning|error`, carries a prescription, no evidence.
- `Verdict` and `Observation` are **distinct types** sharing a `Finding` protocol —
  *not* one dataclass with a disposition discriminator and half-inert optional
  fields. Illegal states are unrepresentable by construction.

**The `REVIEW` action** is a verdict whose remedy is deferred: slop is confident the
structure is anomalous, but the fix is disjunctive and depends on a judgment slop
does not make (e.g. disjoint call-islands — split, or intentional facade?). It is a
verdict, not a third disposition; the conditionality lives in the action. slop does
**not** adjudicate intent — that is a separate concern. `REVIEW` verdicts **cap at
`warning`** (never `error`/exit-1): if we cannot prescribe the fix, we do not
hard-fail the build on it — the same logic that pins observations to `info`, one
tier up.

`confidence` is a verdict-internal scalar (how sure the prescription applies), not a
third axis; an observation has no prescription, so confidence is inert. A
sub-floor-confidence verdict is better demoted to an observation.

## Rule Dispatch and Scope

Scope is **navigable altitude**, not a string tag. Because `ast()` and `lexicon()`
exist on every component (see Per-Entity Projections), a metric is projectable at
any altitude, and the altitudes nest. This unlocks asking the same question at
different scopes — token repetition within one Callable vs. across a whole Package —
which the legacy flat views could not express cleanly.

**Dispatcher-driven, not rule-driven.** A rule *declares* the altitude(s) it is
defined at; the dispatcher walks the component tree and invokes the rule at every
component of that altitude:

```text
for kind in rule.altitudes:
    for component of that kind in corpus:
        rule.check(component, config)     # dispatcher asserts >0 components visited
```

A rule never walks the corpus itself. Two consequences:

- **The silent-no-op bug class becomes unrepresentable.** A rule runs only where it
  declares itself defined, and the dispatcher asserts it visited >0 components — the
  "enabled-but-zero-checked" safeguard is now the dispatch invariant, not a bolt-on.
  The legacy failure (config keyed by category not name, so a rule silently checked
  nothing) cannot recur.
- **Altitude is a false-positive discriminator.** A token dense across a Package is
  domain vocabulary; the same token dense inside one Callable is slop. The signal's
  altitude *profile* corroborates it. (Cross-altitude suppression — mute a
  low-altitude verdict when a higher-altitude observation explains it — is research
  downstream of this spine, not a prerequisite for the executable.)

Declared altitudes mirror the targeting table above: complexity at
`{Callable, Class}`, CK at `{Class}`, Martin at `{Package}`, god_module at
`{Module}`, lexical dispersion scope-polymorphic at `{Class, Module, Package}`,
cross-cutting (hotspots/cycles) at `{Corpus}`.

## Config Model

Config exposes **batteries, not primitives** — the same way the linter surfaces
Martin's distance-from-main-sequence (one threshold) and never Ca/Ce/Na/Nc.

- A **primitive** (hapax ratio, token count, FCA alphabet size) always lives on the
  view and is *never* a config knob.
- A **battery** is a named composite with an equation — the verdict-bearing metric.
  Only the battery threshold is config-surfaced.
- **Algorithm internals** (FCA extents, clustering cutoffs) are module constants,
  not config.
- **Noise floors** (min cluster size, min annotations) are significance gates,
  legitimately config-surfaced even for observations — they govern output volume,
  not the claim.

Thresholds are keyed by **altitude**, validated at config-load against each rule's
declared altitudes — a threshold key the rule does not declare is a load error, not
a silent drop.

**Lexical migration.** Unproven lexical signals ship as **observations with no
verdict threshold**. When a battery proves a consistent signal across corpora it is
promoted: named, given an equation, and given a single config threshold — an
**additive** schema change (old configs still validate), never a subtractive one.
This is *why* primitive knobs must not enter the schema now: removing them later
would be breaking. Triage, not uniform promotion — some signals promote (imposters:
receiver-density × cohesion; sprawl), some stay observations forever
(vocabulary/Zipf, dispersion), some are cut as pure style.

## Derived Graphs (downstream of a working hierarchy)

`DependencyGraph` and `CallGraph` are derived projections, not ownership
containers. They are built *after* the component hierarchy is solid — they
piggyback on it. The hierarchy answers "what owns what"; the graphs answer "what
depends on what" and "what calls what."

These stay **interfaces only** until we know the exact construction parameters.
A shared `Graph` base (common `nodes()`/`edges()`/`neighbors()`) may be worth
extracting once both are concrete, but factoring a hierarchy now — before
CallGraph is even in scope — would be premature. Decide it then, not now.

### DependencyGraph

Built first, because it grounds on import extraction we already trust. Primary
node type is Module; Package / Realm graphs are derived by contracting Module
nodes upward.

```text
DependencyEdge:
  from: Module
  to: Module | Package | Realm | ExternalDependency | UnknownImport
  kind: import | include | require | use | build | reference
  raw_specifier: string
  source_range: source location
  resolved: true | false
```

### CallGraph

Deferred, and entered only with eyes open. A prior call-graph experiment was
reverted: tree-sitter call resolution is approximate, and call-affinity signals
proved orthogonal to the existing rules. If revisited, it is Realm-scoped,
exact-direct-calls first, with every edge carrying honest confidence:

```text
CallEdge:
  from: CallableSymbol
  to: CallableSymbol | ExternalCallable | UnknownCall
  call_site_range: source location
  confidence: exact | probable | unresolved
  dispatch: direct | method | virtual | dynamic | function_pointer | framework

Traversal: known internal -> follow; external -> record boundary, stop;
           unknown dynamic -> record, stop; framework callback -> record entry, do not invent flow.
```

The bar to bring CallGraph back into scope is a concrete rule that needs it and
that the dependency graph plus lexical signals cannot already serve.

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
4. **Build the projections** — one `AST` type (parsed syntax, sliceable) and one
   `Lexicon` type (token-space derived from the AST), each lazily instantiated
   and sliced per component over its extent. Designed fresh, not ported.
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
