# Metric Inventory & Porting Ledger

Every measurement the legacy `src/slop` computes, mapped to its owner in the
component model and its porting status. This is the anti-forgetting checklist:
no metric ports until it appears here with an owner, and none is "done" until
its row says so. Source of truth for *what* to compute; DESIGN.md is the source
of truth for *how* the model is shaped.

Status legend:
- **stub** — abstract signature exists in the spine (`measures.py` / kind ABC); not yet implemented.
- **projection** — signature on the `Lexicon` projection Protocol (`projection.py`); designed in build step 4.
- **graph** — belongs to a derived graph (`DependencyGraph` built step 6; `CallGraph` deferred).
- **rule** — a rule-layer verdict that *consumes* `Lexicon`/`AST` primitives (metric-vs-rule separation); not a projection method.
- **future** — known-desirable, absent from legacy; signature carried as intended behaviour.

## Metric placement classes

- **Aggregatable** — defined at the Callable leaf, summed at every altitude above (`ComplexityMeasures` on `Component`): cyclomatic, cognitive, combinatorial, volume, sloc.
- **Position-unique** — defined at exactly one kind. Everything else below.
- **WMC is not a metric, it's a weighting family.** CK define WMC = Σ method weights, weight unspecified. weight=cyclomatic → WMC = `class.cyclomatic()` (the aggregatable Σ); weight=1 → WMC = `method_count()` (NOM). Both already exist, so there is no standalone `wmc()` — it would duplicate one of them.

## Rules → owner → status (29 legacy rules)

| Legacy rule | Measures | New owner.method | Status |
|---|---|---|---|
| complexity.cyclomatic | McCabe CCN | `Callable.cyclomatic` (+ container Σ) | stub |
| complexity.cognitive | Campbell cognitive | `Callable.cognitive` | stub |
| complexity.combinatorial | Nejmeh NPath | `Callable.combinatorial` | stub |
| complexity.volume | Halstead volume | `Callable.volume` / `Callable.halstead` | stub |
| complexity.density | Halstead difficulty (non-additive) | `Callable.halstead_density` | stub |
| coupling | CK CBO | `Class.cbo` / `Class.ck` | stub |
| inheritance.depth | CK DIT | `Class.dit` | stub |
| inheritance.children | CK NOC | `Class.noc` | stub |
| types.hidden_mutators | in-place param mutation | `Callable.mutated_parameters` | stub |
| types.magic_literals | non-trivial numeric literals | `Callable.magic_literals` | stub |
| types.sentinels | stringly-typed sentinel params | `Callable.sentinel_parameters` | stub |
| god_module | top-level definition count | `Module.definition_count` | stub |
| types.escape_hatches | escape-hatch annotation density | `Module.escape_hatch_density` | stub |
| redundancy | sibling-callee overlap | `Module.redundant_siblings` | stub |
| duplication | type-2 clone clusters | `Module.clone_clusters` (+ `Corpus.duplication`) | stub |
| lexical.confusion | disjoint call-islands (structural, NOT lexical) | `Module.call_islands` | stub |
| rigidity | Martin zone of pain | `Package.in_zone_of_pain` / `martin_metrics` | stub |
| uselessness | Martin zone of uselessness | `Package.in_zone_of_uselessness` / `martin_metrics` | stub |
| lexical.runts | trivial single-module package | `Package.is_runt` | stub |
| hotspots | churn × complexity | `Corpus.hotspots` | stub |
| orphans | unreferenced symbols | `Corpus.orphans` | stub |
| deps | import cycles (Tarjan SCC) | `DependencyGraph.cycles` / `Corpus.dependency_cycles` | graph |
| lexical.stutter | scope-token repetition | rule consuming `Lexicon` | rule |
| lexical.verbosity | over-long names | rule consuming `Lexicon` | rule |
| lexical.hammers | catchall vocabulary | rule consuming `Lexicon` | rule |
| lexical.sprawl | closed-alphabet sprawl (FCA) | rule consuming `Lexicon` | rule |
| lexical.imposters | camouflaged params | rule consuming `Lexicon` | rule |
| lexical.slackers | template-refusing siblings | rule consuming `Lexicon` | rule |
| vocabulary | Zipf/hapax distribution (observation) | rule consuming `Lexicon` | rule |

## Carried but not in legacy

| Metric | Owner.method | Status | Note |
|---|---|---|---|
| CK LCOM | `Class.lcom` | future | Completes the CK suite; returns `None` until ported. |
| Lexical concept-dispersion | rule consuming `Lexicon` (`hapax_ratio`, `significant_token_count`) | future | The user's "confusion" sense — too many distinct concepts in one namespace. Scope-polymorphic. Verdict = hapax residual above Zipf baseline, maturity-gated (absolute hapax is invariant ~0.49). A rule, not a Lexicon method. Distinct from `Module.call_islands`. |
| CallGraph | `graph/call.py` | deferred | Re-entry bar in DESIGN.md: a rule the dependency graph + lexical signals can't already serve. |

## Open placement questions

- **WMC weighting.** CK leave the method weight open; legacy used cyclomatic-sum (which collapses WMC into `class.cyclomatic`). New `wmc()` must pick a real definition (unweighted method count, or configurable weight) to stay distinct.
- **Confusion altitude.** Placed at `Module.call_islands` (intra-module topology). Whether it stays a structural Module metric or moves behind the CallGraph bar is unresolved — see DESIGN.md.
- **`Module` relational metrics** (redundant_siblings / call_islands / clone_clusters) currently sit on `ModuleMeasures`; they may migrate to a graph projection if a cross-module form is needed.
