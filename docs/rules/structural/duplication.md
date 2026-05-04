# structural.duplication

**What it measures:** Type-2 clone density across the codebase — fraction of functions whose AST body is structurally identical to another's after identifier normalization. Type-2 clones differ only in identifier names (and optionally literals); the control-flow shape and structure are identical.

**Default threshold:** flag when `> 5%` of functions are cloned. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `threshold` | `0.05` | Maximum tolerated clone fraction (0.0–1.0). |
| `min_leaf_nodes` | `10` | Minimum AST leaf count for a function to be considered; skips trivial one-liner bodies. |
| `min_cluster_size` | `2` | Only report clusters of at least this many members. |

## What it prevents

Functions identical in structure with only variable names swapped. A bug fixed in one is silently left in the other.

```python
# ❌ flagged — same structure, different names (Type-2 clone)
def calculate_discount(price, rate):
    base = price * rate
    adjusted = base * 0.9
    return round(adjusted, 2)

def calculate_fee(amount, percentage):
    base = amount * percentage
    adjusted = base * 0.9
    return round(adjusted, 2)

# Fix the rounding logic in calculate_discount.
# calculate_fee still has the old version.
```

**When to raise it:** Codebases with many parallel handler implementations that intentionally mirror each other (e.g., per-type serializers, language-specific formatters). Raising to 10–15% accommodates this.

**When to lower it:** Greenfield projects pushing for tight DRY discipline. `threshold = 0.02` catches clone clusters early.

```toml
[rules.structural.duplication]
threshold = 0.05
min_leaf_nodes = 10
min_cluster_size = 2
severity = "warning"
```
