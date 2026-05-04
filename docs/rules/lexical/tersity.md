# lexical.tersity

**What it measures:** Fraction of identifiers that are ≤ 2 characters within a function body. Acts as a *guardrail* against over-correction into cryptic single-letter naming once `lexical.verbosity` is in force.

**Default threshold:** `> 50%` of identifiers ≤ 2 chars. Severity `warning`.

**What the numbers mean:** Conventional indices (`i`, `j`, `k`) and short math names (`x`, `y`) are not penalised in isolation — only when a function leans on them so heavily that the majority of its identifier surface is cryptic. A 50% threshold tolerates loops and math-heavy code while flagging functions that have been compressed past the point of readability.

## What it prevents

Everything shrunk to a single letter. You read the function three times and still can't tell what `v`, `r`, or `t` represent.

```python
# ❌ flagged — 6 out of 8 identifiers are ≤ 2 chars
def process(d):
    r = []
    for i, v in enumerate(d):
        if v > t:
            r.append(i)
    return r

# ✓
def find_above_threshold(data):
    result = []
    for i, value in enumerate(data):
        if value > threshold:
            result.append(i)
    return result
```

**When to raise it:** Numerical or DSL-interpreter code with heavy single-letter convention. 70% is reasonable for tight numerics.

**When to lower it:** Application code where conventional short names should be rare. 30% catches drift toward cryptic naming earlier.

```toml
[rules.lexical.tersity]
max_density = 0.50
```
