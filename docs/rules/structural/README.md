# Structural rules

Structural rules measure the shape of code: control flow, dependency graphs, class hierarchies, package graphs, type discipline, and change history. They operate on deterministic tree traversals and graph algorithms over source and git history. No models, no embeddings, no external corpora.

This is the core suite for slop. It is cheap, deterministic, and well-understood — every project should run it.

## Rule inventory

### structural.complexity — per-function control flow

| Rule | Default | Citation |
|---|---|---|
| [`structural.complexity.cyclomatic`](complexity/cyclomatic.md) | CCX > 10 | McCabe 1976 |
| [`structural.complexity.cognitive`](complexity/cognitive.md) | CogC > 15 | Campbell 2018 |
| [`structural.complexity.npath`](complexity/npath.md) | NPath > 400 | Nejmeh 1988 |

### structural.class — class-level structure

| Rule | Default | Citation |
|---|---|---|
| [`structural.class.complexity`](class/complexity.md) | WMC > 40 | Chidamber & Kemerer 1994 |
| [`structural.class.coupling`](class/coupling.md) | CBO > 8 | Chidamber & Kemerer 1994 |
| [`structural.class.inheritance.depth`](class/inheritance/depth.md) | DIT > 4 | Chidamber & Kemerer 1994 |
| [`structural.class.inheritance.children`](class/inheritance/children.md) | NOC > 10 | Chidamber & Kemerer 1994 |

### structural.types — type discipline

| Rule | Default | What it catches |
|---|---|---|
| [`structural.types.sentinels`](types/sentinels.md) | ≤ 8 values | `str` parameters that should be `Literal`/enum |
| [`structural.types.hidden_mutators`](types/hidden_mutators.md) | any mutation | Functions that mutate collection parameters in place |
| [`structural.types.escape_hatches`](types/escape_hatches.md) | > 30% | Files dominated by `Any`/`interface{}` annotations |

### Other structural rules

| Rule | Default | Citation / signal |
|---|---|---|
| [`structural.hotspots`](hotspots.md) | 14d window | Tornhill 2015 |
| [`structural.packages`](packages.md) | D' > 0.7 | Martin 1994 |
| [`structural.deps`](deps.md) | any cycle | Tarjan 1972 |
| [`structural.local_imports`](local_imports.md) | any (warning) | imports inside function bodies |
| [`structural.redundancy`](redundancy.md) | ≥ 3 shared | sibling functions with overlapping callees |
| [`structural.duplication`](duplication.md) | > 5% | Type-2 clone detection |
| [`structural.god_module`](god_module.md) | > 20 | breadth of top-level definitions |
| [`structural.orphans`](orphans.md) | disabled | unreferenced symbols (advisory) |

## Category properties

- **Substrate:** AST, import graph, inheritance graph, commit history, file size.
- **Compute profile:** fast. Every rule runs in seconds on repositories of tens of thousands of files. No network, no external models, no precomputed artifacts.
- **Determinism:** full. Identical source and identical git history produce identical output.
- **Failure modes:** parser edge cases, threshold miscalibration against a language idiom (documented per rule), shallow clones breaking history-dependent rules.
- **Interpretation burden:** low. Every violation can be explained in one or two sentences to anyone familiar with standard software-engineering literature.

## Language support

| Language | Complexity | Hotspots | Packages | Deps | Class | Local imports |
|---|---|---|---|---|---|---|
| Python | yes | yes | yes | yes | yes | yes (AST) |
| JavaScript | yes | yes | partial* | yes | yes | — |
| TypeScript | yes | yes | yes | yes | yes | — |
| Go | yes | yes | yes | yes | yes | — |
| Rust | yes | yes | partial* | partial | yes | yes (text) |
| Java | yes | yes | yes | yes | yes | — |
| C# | yes | yes | yes | yes | yes | — |
| Julia | yes | yes | — | partial | — | yes (AST) |

*Packages rule degrades where the language lacks a native abstract-type concept distinct from concrete classes.*

Unsupported languages are silently excluded from the relevant rules rather than erroring.
