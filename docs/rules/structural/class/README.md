# structural.class

Class-level metrics from the Chidamber & Kemerer (1994) family plus weighted methods. All rules in this group can be disabled in non-OOP codebases without affecting other rules.

| Rule | Default | Citation |
|---|---|---|
| [`structural.class.complexity`](complexity.md) | WMC > 40 | Chidamber & Kemerer 1994 |
| [`structural.class.coupling`](coupling.md) | CBO > 8 | Chidamber & Kemerer 1994 |
| [`structural.class.inheritance.depth`](inheritance/depth.md) | DIT > 4 | Chidamber & Kemerer 1994 |
| [`structural.class.inheritance.children`](inheritance/children.md) | NOC > 10 | Chidamber & Kemerer 1994 |

See [`inheritance/`](inheritance/README.md) for inheritance-graph-specific metrics.
