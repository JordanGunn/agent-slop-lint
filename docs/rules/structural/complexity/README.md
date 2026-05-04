# structural.complexity

Per-function control-flow measurements. These three rules form the core complexity baseline for slop. Cyclomatic and cognitive complexity should rarely be disabled; if noisy, raise thresholds rather than turning off. NPath also belongs here because it measures combinatorial execution paths through a function.

| Rule | Default | Citation |
|---|---|---|
| [`structural.complexity.cyclomatic`](cyclomatic.md) | CCX > 10 | McCabe 1976 |
| [`structural.complexity.cognitive`](cognitive.md) | CogC > 15 | Campbell 2018 |
| [`structural.complexity.npath`](npath.md) | NPath > 400 | Nejmeh 1988 |

```toml
[rules.structural.complexity]
cyclomatic_threshold = 10
cognitive_threshold = 15
npath_threshold = 400
```
