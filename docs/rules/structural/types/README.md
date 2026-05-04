# structural.types

Type-discipline rules. They detect three failure modes around the type system: stringly-typed sentinels, hidden in-place mutation, and escape-hatch type density. All three ship at severity `warning`.

| Rule | Default | What it catches |
|---|---|---|
| [`structural.types.sentinels`](sentinels.md) | ≤ 8 values | `str` parameters that should be `Literal[...]` or an enum |
| [`structural.types.hidden_mutators`](hidden_mutators.md) | any mutation | Functions that mutate collection parameters in place |
| [`structural.types.escape_hatches`](escape_hatches.md) | > 30% | Files dominated by `Any` / `interface{}` / `any` annotations |
