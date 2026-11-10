# Metric Inventory & Porting Ledger

Every measurement the legacy `src/slop` computes, mapped to its owner in the
component model and its porting status. This is the anti-forgetting checklist:
no metric ports until it appears here with an owner, and none is "done" until
its row says so. Source of truth for *what* to compute; DESIGN.md is the source
of truth for *how* the model is shaped.

Status legend:
- **done** — implemented + oracle-verified across the 11 grammars.
- **deferred** — blocked on a derived-graph bar (see DESIGN.md); returns `None` /
  raises with a pointer.
- **future** — known-desirable, absent from legacy; signature carried as intended behaviour.

## Metric placement classes

- **Aggregatable** — defined at the Callable leaf, summed at every altitude above (`ComplexityMeasures` on `Component`): cyclomatic, cognitive, combinatorial, volume, sloc.
- **Position-unique** — defined at exactly one kind. Everything else below.
- **WMC is not a metric, it's a weighting family.** CK define WMC = Σ method weights, weight unspecified. weight=cyclomatic → WMC = `class.cyclomatic()` (the aggregatable Σ); weight=1 → WMC = `method_count()` (NOM). Both already exist, so there is no standalone `wmc()` — it would duplicate one of them.

## Measures → owner → status

| Measure | What it captures | New owner.method | Status |
|---|---|---|---|
| McCabe CCN | path coverage | `Callable.cyclomatic` (+ container Σ) | done |
| Campbell cognitive | reading difficulty | `Callable.cognitive` | done |
| Nejmeh NPath | acyclic execution paths | `Callable.combinatorial` | done |
| Halstead volume | information content | `Callable.volume` / `Callable.halstead` | done |
| Halstead difficulty | operator/operand density (non-additive) | `Callable.halstead_density` | done |
| magic literals | non-trivial numeric literals | `Callable.magic_literals` | done (measure; rule deferred to the structural-analysis layer) |
| CK CBO | class coupling | `Class.cbo` / `Class.ck` | done |
| CK DIT | inheritance depth | `Class.dit` | done |
| CK NOC | subclass fan-out | `Class.noc` | done |
| god module | top-level definition count | `Module.definition_count` | done |
| Type-2 clones | clone clusters | `Module.clone_clusters` (+ `Corpus.duplication`) | done |
| Martin zone of pain | stable + concrete package | `Package.in_zone_of_pain` / `martin_metrics` | done |
| Martin zone of uselessness | unstable + abstract package | `Package.in_zone_of_uselessness` / `martin_metrics` | done |
| hotspots | churn × complexity | `Corpus.hotspots` | done |
| orphans | unreferenced symbols | `Corpus.orphans` | done |
| import cycles | Tarjan SCC | `DependencyGraph.cycles` / `Corpus.dependency_cycles` | done |
| Zipf/hapax distribution | identifier token shape (observation) | rule consuming `Lexicon` (`distribution`, `narrate`) at `Package` | done |

## Carried but not in legacy

| Metric | Owner.method | Status | Note |
|---|---|---|---|
| CK LCOM | `Class.lcom` | future | Completes the CK suite; returns `None` until ported. |
| CallGraph | `graph/call.py` | deferred | Re-entry bar in DESIGN.md: a rule the dependency graph + lexical signals can't already serve. |

## Open placement questions

- **WMC weighting.** CK leave the method weight open; legacy used cyclomatic-sum (which collapses WMC into `class.cyclomatic`). New `wmc()` must pick a real definition (unweighted method count, or configurable weight) to stay distinct.
- **Package carving — resolved.** Carving now uses `grammar.resolve_packages` (flat, `__init__`-gated, rel-path-named, matching the legacy package model), with a per-directory fallback for loose scripts. Verified: package boundaries + Ca/Ce/I/A match the oracle exactly on `src/slop` (15 packages). Residual: for **class-less packages** the legacy reports `A=None`/`distance=None`/zone `unknown`, while `PackageMetrics`'s non-optional float fields show `A=0.0` and a computed `distance`. Zone verdicts (`in_zone_of_pain`/`uselessness`) guard on definedness and are correct. Closing this exactly needs `PackageMetrics.{instability,abstractness,distance}: float | None` — a `metrics/structural/records.py` change (the protected interfaces), deferred pending approval.