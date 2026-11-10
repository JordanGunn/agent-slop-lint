# slop rules

slop ships **12 rules**, language-agnostic across 11 grammars. A rule is a threshold on a
published measure: it reports a violation when the measure is strictly greater than the
limit. The authoritative, always-current reference is the tool itself:

```bash
slop rules     # name, enabled state, altitude, description for every rule
slop schema    # the exact config shape (thresholds + params), generated from the registry
```

Each rule's rationale (what it measures, why, the citation) lives in its **module
docstring** under `src/slop/rules/`. That is the single source of truth; this page is only
a map.

## The rules

| Rule | Altitude | Default limit | Source |
|---|---|---|---|
| `complexity.cyclomatic` | callable | 10 | McCabe (1976) |
| `complexity.cognitive` | callable | 15 | Campbell (2018) |
| `complexity.combinatorial` | callable | 400 | NPath, Nejmeh (1988) |
| `structure.god-module` | module | 20 top-level definitions | module size boundary |
| `structure.rigidity` | package | D' 0.7 | Martin (1994, 2002), Zone of Pain |
| `structure.uselessness` | package | D' 0.7 | Martin (1994, 2002), Zone of Uselessness |
| `structure.dependency-cycles` | corpus | none (any cycle) | Acyclic Dependencies Principle |
| `structure.duplication` | corpus | 2 clones (`params.min_leaf_nodes` = 10) | Type-2 clones |
| `class.coupling` | class | CBO 8 | Chidamber & Kemerer (1994) |
| `class.inheritance-depth` | class | DIT 4 | Chidamber & Kemerer (1994) |
| `class.children` | class | NOC 10 | Chidamber & Kemerer (1994) |
| `class.cohesion` (**off by default**) | class | LCOM4 groups 1 | Hitz & Montazeri (1995) |

`class.cohesion` counts the groups of methods joined through shared instance members and
lists them. It is measured for Python, JavaScript and TypeScript; elsewhere a bare `x` can
mean `this.x`, which syntax alone cannot resolve. Enable it with
`[rules."class.cohesion"] enabled = true`. `slop shape` prints the CK profile and cohesion
groups of every class regardless of these rules.

## Output and exit codes

```
src/app/config.py:12:1: complexity.cyclomatic app.config.load has cyclomatic complexity 14 (limit 10)
Found 1 violation.
```

One `path:line:column: rule message` line per violation. Exit `0` none, `1` any violation,
`2` error. Suppress a violation inline with `slop: ignore[rule]` on its line.

See [the configuration reference](../CONFIG.md) for thresholds, params and suppression.
