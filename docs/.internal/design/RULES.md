## Rules

A rule is a threshold on a measure. It declares the scope kinds ("altitudes") it is defined
at, the dispatcher calls it once per component of that kind, and it returns zero or more
`Violation` records. A violation is emitted when the measure is **strictly greater** than
the limit. Nothing else (no ranking, no advice) is part of a rule's output.

## Targeting table

Each rule resolves to exactly one altitude. Limits are the defaults; `slop schema` prints
the live values.

| Rule | Altitude | Measure | Limit | Source |
|---|---|---|---|---|
| `complexity.cyclomatic` | callable | cyclomatic complexity | 10 | McCabe 1976 |
| `complexity.cognitive` | callable | cognitive complexity | 15 | Campbell 2018 |
| `complexity.combinatorial` | callable | NPath (acyclic paths) | 400 | Nejmeh 1988 |
| `structure.god-module` | module | top-level definitions | 20 | size boundary |
| `structure.rigidity` | package | Martin D', stable and concrete | 0.7 | Martin 1994, 2002 |
| `structure.uselessness` | package | Martin D', unstable and abstract | 0.7 | Martin 1994, 2002 |
| `structure.dependency-cycles` | corpus | strongly connected module sets | none | Acyclic Dependencies Principle (Martin 2002, Lakos 1996) |
| `structure.duplication` | corpus | Type-2 clone clusters (`params.min_leaf_nodes` = 10) | 2 clones | Type-2 clone taxonomy |
| `class.coupling` | class | CBO | 8 | Chidamber & Kemerer 1994 |
| `class.inheritance-depth` | class | DIT | 4 | Chidamber & Kemerer 1994 |
| `class.children` | class | NOC | 10 | Chidamber & Kemerer 1994 |
| `class.cohesion` (off by default) | class | LCOM4 group count | 1 | Hitz & Montazeri 1995 |

Metrics resolve to a home altitude: complexity is computed per callable; CK and LCOM4 per
class; Martin's metrics per package; the import graph and clone detection need the whole
corpus. WMC is not a metric of its own but a weighting family (weight = cyclomatic gives
`class.cyclomatic()`, weight = 1 gives `method_count()`).

Measures that no rule reports (`Structure.hotspots`, churn x complexity after Tornhill;
`Structure.orphans`, unreferenced top-level symbols) stay on the `Structure` view as dormant
measures.

## Dispatch

A rule never walks the corpus itself:

```text
for kind in rule.altitudes:
    for component of that kind in corpus:
        rule.check(component, config)
```

Consequences:

- A rule runs only where it declares itself defined, and a threshold keyed to an altitude
  the rule does not declare is a config load error, so a mis-keyed config cannot make a rule
  silently check nothing.
- The dispatcher records how many components each rule visited; a rule that visited zero is
  listed under `zero_visited` in the JSON report.

## Violation

`Violation(rule, path, line, column, message, value=None, threshold=None)` is a frozen
record. `Violation.at(scope, rule, message, value=, threshold=)` places it at the module,
class or callable that owns it (line and column of its syntax node, 1-based), or at a
package's directory. Corpus-altitude rules place a violation at the first member (by path)
of the cycle or clone cluster they report.

The dispatcher sorts violations by (path, line, column, rule) and drops any whose reported
line contains `slop: ignore` (all rules) or `slop: ignore[rule, family]` (the named rules;
a family prefix such as `complexity` covers `complexity.cyclomatic`). The exit code is 1 if
any violation remains, else 0.
