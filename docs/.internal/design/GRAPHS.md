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
