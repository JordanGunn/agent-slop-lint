# structural.types.hidden_mutators

**What it measures:** Functions that mutate collection-typed parameters in place (`.append`, `.extend`, `.add`, `.update`, etc.). Mutating a passed-in collection is an out-parameter pattern — the caller's data is silently modified as a side effect. It makes call-site reasoning harder, prevents pure functional testing, and often signals that the function should instead return a new collection.

**Default threshold:** flag any mutation of a collection-typed parameter. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `require_type_annotation` | `true` | When true, only flag parameters with explicit collection type annotations (`list`, `dict`, `set`, etc.). When false, any mutated parameter is flagged. |
| `min_mutations` | `1` | Minimum number of mutation calls in a function before flagging it. |

## What it prevents

A function that silently modifies the caller's data as a side effect. The caller passes in a list expecting the function to read it, and gets it back changed without any indication at the call site.

```python
# ❌ flagged
def add_defaults(items: list):
    items.append("default")  # caller's list is modified in place

my_list = ["a", "b"]
add_defaults(my_list)
print(my_list)  # ["a", "b", "default"] — surprise

# ✓ return a new list instead
def add_defaults(items: list) -> list:
    return [*items, "default"]
```

**When to raise it:** Codebases that intentionally use builder-style helpers that mutate a passed-in accumulator. Raising `min_mutations` to 3+ trims smaller cases.

**When to disable:** Performance-critical code where in-place mutation is an explicit contract documented elsewhere.

```toml
[rules.structural.types.hidden_mutators]
require_type_annotation = true
min_mutations = 1
severity = "warning"
```
