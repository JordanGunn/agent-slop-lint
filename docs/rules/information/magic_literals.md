# information.magic_literals

**What it measures:** Number of distinct non-trivial numeric literals embedded in a function body. A literal with no symbolic name forces the reader to guess its meaning from context; clusters of such literals in a single function are a reliable signal that the function embeds domain logic that should live in named constants or configuration.

**Default threshold:** `> 3` distinct non-trivial literals per function. Severity `warning`.

**Trivial constants excluded from counting:** `0`, `1`, `-1`, `2`. See `_structural/magic_literals.py` for the full exclusion list.

## What it prevents

Numbers embedded in logic with no names attached. You can see *that* they're there but not *why* those specific values were chosen, whether they're configurable, or where they came from.

```python
# ❌ flagged (5 unexplained literals)
def is_eligible(user):
    return (
        user.age >= 21 and
        user.score > 650 and
        user.income >= 35000 and
        user.debt_ratio < 0.43 and
        user.history_months >= 24
    )
# Where did 650 come from? Is 0.43 a regulation? Can 35000 change?

# ✓
MIN_AGE            = 21
MIN_CREDIT_SCORE   = 650
MIN_INCOME         = 35_000
MAX_DEBT_RATIO     = 0.43
MIN_HISTORY_MONTHS = 24
```

**When to raise it:** Numerics-heavy code where literal constants are intrinsic to the algorithm (signal-processing coefficients, embedded math). Raising to 6–8 trims noise.

**When to lower it:** Greenfield projects pushing for named constants. `threshold = 1` catches every cluster.

```toml
[rules.information.magic_literals]
threshold = 3
severity = "warning"
```
