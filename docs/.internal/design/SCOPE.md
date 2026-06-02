## Scope Subsystem — the forest/ownership layer, decoupled from metrics

> **Status: implemented** on `dev`. `component/` and `model/` are retired; `scope/`,
> `metrics/structural/`, and `graph/` are in place and the scope entities are
> metric-free. The deferred items below — the metric *home* (peer view vs
> linter-internal) and the `Metric` registry (D) — remain open.

The v3 `component/` package fused two concerns the way the legacy lexical layer
fused vocabulary with rule policy: the **scope/ownership model** (the
Corpus→Realm→Package→Module→Class→Callable entity tree, identity, extent, carving)
and the **metric inventory** (the per-altitude measure ABCs in `measures.py`, the
result records in `metrics.py`, and the compute in `model/`). The fusion is by
inheritance — `Scope(ComplexityMeasures)`, `Callable(SymbolContainer,
CallableMeasures)` — and runs into the concrete layer, where `model/components.py`'s
`_Base` mixes `id`/`extent`/`children` with `cyclomatic`/`_sum`. This subsystem gives
the scope concern one owner and makes it, like `ast/` and `lexicon/`, a package with a
single clear job.

### Principle

`scope/` is **strictly the forest-and-ownership model**: it identifies entities, holds
their extent, carves them from the AST forest, and exposes them as addressable
*regions*. It does not compute. The governing test for every member: *is this about
which entities exist, how they nest, and how they are identified — independent of any
measurement?* Identity, extent, containment, carving, navigation — yes. Cyclomatic,
CK, Martin, clones — no; those are measurements and live above, in `metrics/`.

This is the same discipline as `ast/`/`lexicon/`. `scope/` *uses* both kernels — it
carves from `ast` and projects to `lexicon` — but nothing above it (metrics, rules)
leaks back down: `scope/` imports nothing from `metrics`, `linter`, or `rules`.

### Why the cut (and why now)

Two kernels are strong and standalone. The scope concern was the remaining tangle, and
it carried decisions that predate those kernels: a provisional `capability.HasClasses`
"pending the grammar-paradigm port" that has since landed in `ast/paradigm/`; a
`projection.py` Lexicon Protocol that now shadows the real `lexicon.Lexicon`; and
corpus-global indexes (`class_index`, `dep_graph`) bolted onto entity attributes. The
metric *home* — whether the structural metric surface ends up a `metrics/structural/`
view or linter-internal — is a separate, deferred conversation; this subsystem does not
settle it. It only **relocates** the inventory intact and severs it from the entities.

### Layering

```text
span · identity                         primitives (zero-dep value types)
   │       │
  ast   lexicon                         kernels — peers; neither imports the other
        \   │   /
         scope                          forest/ownership: regions + carve + analysis-context
        /   │   \
metrics/structural   metrics/lexical    slop's measurements over (region, context) · over lexicon
         \   │   /
          linter                        rules: thresholds + verdicts over metrics
```

One rule keeps it acyclic — the same rule that made `lexicon/` work: **views take
plain data, never scope objects.** A metric is computed over `(region, context)` —
an addressable region plus the corpus-global indexes — both plain. So `scope →
metrics` never happens; `metrics → ast`/`identity` only.

### A — scope is a minimal *region provider*

A scope exposes a small, stable surface and **no per-view methods**:

```python
id · kind · extent · nodes() · children · navigation · context
```

The canonical way to obtain a view is `View.over(region)`, owned by the *view's* own
layer (`Lexicon.over(region)`, `Structure.over(region, context)`) — never a method
per view on the scope. Adding a future view (semantic, control-flow, security) then
touches zero scope code. `scope.lexicon()` may survive only as optional sugar that
delegates to `Lexicon.over(self)`. The point: scope is a passive, minimal data
provider; the views are the active consumers.

### B — corpus-global graphs/indexes are an analysis-context, not entity attributes

CK needs the whole-corpus class hierarchy; Martin needs the module dependency graph;
future metrics will need a call graph, an inheritance graph, dataflow. These are
corpus-global derived artifacts. They do **not** live as attributes on entities
(`Class._class_index`, `Package._dep_graph` today). They live in an **analysis-context**
held at the `Corpus` root; a region reaches it via the owner chain (`region.context`);
metrics that need cross-scope data pull it from there. New graphs are added to the
context without touching scope.

### C — logical vs physical identity

`ScopeId = (kind, qualname, spans)` bakes byte offsets into identity, so a
one-byte edit shifts every downstream id — hostile to caching, watch-mode, and
cross-run diffing. The id gains a stable **logical key** (kind + qualname) distinct
from the volatile **physical extent** (spans). Additive first: keep current equality,
expose the logical key; full exploitation (graph-keying / diffing on the logical key)
follows when a consumer needs it. The point is to stop *precluding* incremental
analysis, not to build it now.

### The interface — addressable regions

A region is the unit a view consumes. A single scope is a region; so is a **selection**
of scopes (a set of regions is itself a region to the view layer), so granular scoping
composes uniformly: `Lexicon.over(selection)`, `Structure.over(selection, context)`.
This is the legacy pain point dissolved — "a clean lexicon / metrics over *this*
region" works at any altitude and over any union, because a view is a function of an
extent and extents compose.

Honest limit: a Lexicon over A∪B is always well-defined (more vocabulary), and the
*additive* structural metrics (cyclomatic, sloc, volume) sum over any union; the
*altitude-bound* ones (CK at Class, Martin at Package) stay altitude-bound and are
silent over an arbitrary union rather than reporting a false number.

### The metric relationship — preserve the inventory, name the families

The metric inventory is relocated, not redesigned. It splits by what it measures over:

- `metrics/structural/` — computed over `ast` nodes + the analysis-context. Holds the
  result records (today's `metrics.py`) and the compute moved from `model/`
  (`complexity`, `halstead`, `ck`←`class_index`, `martin`, `relational`, `orphans`,
  `hotspots`, `annotations`, `imports`). No separate structural *kernel*: `ast` is the
  structural substrate, and these metrics have no out-of-linter reuse story (yet) to
  justify one.
- `metrics/lexical/` — slop's invented lexical *signals* (sprawl, stutter-overlap,
  hammers) composed over the `lexicon/` kernel. **Not** a rename of the kernel:
  `lexicon/` stays the standalone linguistic library; `metrics/lexical/` is the slop
  layer above it. (Empty/near-empty until the lexical rules are ported.)

`metrics/` is an organizational umbrella over two independent families (a shared
consumption pattern, not shared code) plus one thin contract:

#### D — a metric registry

A `Metric` descriptor (name, altitude(s), result type, additive?) and a registry,
mirroring the rule registry, so config schema, docs, and the per-altitude capability
map derive from one source rather than scattered hand-maintenance — extending the
dispatcher's "no silent no-op" guarantee from rules to metrics. Cross-family
**batteries are composite metrics**: the composite *measurement* (e.g. imposters'
body-Jaccard × receiver-density, joined by `Span`) lives in `metrics/` consuming both
families; only the threshold/verdict is a rule. The metric/rule line stays clean even
for batteries.

### Package layout

```text
identity.py        ScopeKind / CallableKind / ScopeId(+logical) / Extent  (low base)
scope/
  base.py          Scope (ABC) + AggregateContainer / SymbolContainer  (region surface, no metrics)
  aggregate.py     Corpus / Realm / Package
  symbol.py        Module / Class / Callable
  capability.py    paradigm capability — derived from ast.Paradigm (HasClasses retired)
  concrete.py      the realizations (was model/components.py, minus metric methods)
  carve.py         scan + the analysis-context assembly (class index, dep graph)
  context.py       AnalysisContext — corpus-global indexes, held at the Corpus root
```

`model/` dissolves: its concrete entities + carve move here; its metric compute +
records move to `metrics/structural/`; its lexicon bridge becomes the
`Lexicon.over(region)` projection.

### Naming

Package `scope/`; the root ABC is `Scope` (reclaiming the term — the legacy "don't
call it Scope" note was a v2-only collision that does not exist in v3, and the user's
mental model is "scope"). `AggregateContainer`/`SymbolContainer` and the six kinds keep
their names. The rename's churn is shielded by the same re-export pattern that shielded
the `Span` move.

### Boundary — scope identifies, views measure, the linter judges

> **`scope/` owns the entity tree, its identity, and its extent. Measurements live in
> `metrics/`; verdicts live in `linter/`. A metric method on a scope entity is the
> tell.**

The risk to avoid is the structural form of the v2 sin — the ownership model absorbing
metric compute (which is exactly the fusion being undone). A `cyclomatic()` on a scope
entity, or a `_class_index` attribute on a `Class`, is the smell.

### Migration path (staged additive-then-subtractive; green at every boundary)

The full extraction is sequenced so the test suite is green at each phase boundary —
the accepted "breakage" of severing metrics never lands on disk, because the new path
is added before the old is removed:

1. **Identity** → `slop/identity.py`; `component.identity` re-exports; add the logical key.
2. **`metrics/structural/`** stood up *additively*; entities temporarily delegate their
   metric methods to it; the registry lands; graph records relocate.
3. **Analysis-context + region protocol**; indexes move off entities; `ast.Node` grows
   `callables()`/`classes()`/`methods()`; lexicon projection inverted; capability →
   `ast.Paradigm`.
4. **Rewire** the `cyclomatic`/`call-islands` rules onto `metrics/structural`, *then*
   sever the metric methods from the entities.
5. **Extract `scope/`**; re-point the blast-radius imports; retire `component/`/`model/`.
6. **Prove granular scoping** — a `Selection` and tests for a view over one scope and
   over a union of scopes.
