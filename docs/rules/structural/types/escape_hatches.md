# structural.types.escape_hatches

**What it measures:** Density of escape-hatch type annotations per file — the language's "I give up on the type system" type: Python `Any`, Go `any`/`interface{}`, TypeScript `any`, Java `Object`, C# `dynamic`. High density signals that the type system has been bypassed across a wide surface.

**Default threshold:** flag files where `> 30%` of type annotations are escape hatches. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `threshold` | `0.30` | Maximum tolerated density (0.0–1.0). |
| `min_annotations` | `5` | Minimum annotation count before density is computed. Avoids noise from files with only 1–2 annotations. |

## What it prevents

Type annotations that say "I give up." When `Any` is everywhere the type checker can't catch anything, and the annotations become pure decoration — the false sense of a typed codebase.

```python
# ❌ flagged (4 out of 5 annotations are Any)
def process(data: Any, config: Any) -> Any:
    result: Any = transform(data, config)
    validated: Any = check(result)
    return validated

# The type checker approves everything here.
# All bugs surface at runtime only.
```

**When to raise it:** Codebases doing legitimate generic-container work or interop layers (TypeScript adapters around untyped libraries, Python boundary code receiving JSON). Raising to 50% accommodates this.

**When to lower it:** Greenfield projects pushing for strict typing. `threshold = 0.10` catches escape-hatch drift early.

```toml
[rules.structural.types.escape_hatches]
threshold = 0.30
min_annotations = 5
severity = "warning"
```
