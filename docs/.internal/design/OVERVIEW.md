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
