# information.difficulty

**What it measures:** Halstead's (1977) Difficulty — `D = (n1/2) × (N2/n2)` where n1 is unique operators, n2 is unique operands, and N2 is total operand occurrences. Difficulty proxies the cognitive burden of reading one line: how many operators the reader has to track and how often operands repeat.

**Default threshold:** `D > 30`

**What the numbers mean:** A simple arithmetic function lands around D=5–10. Functions approaching D=30 use most of their language's operator surface and reuse a lot of operands — typical of parsers, expression evaluators, or densely-fused pipelines. D=50+ is almost always a sign that a function is doing the work of three.

## What it prevents

Dense, operator-heavy lines where every character carries meaning and reading speed drops to a crawl. High difficulty often hides in short functions that look simple until you try to modify them.

```python
# ❌ flagged (D ≈ 38 — six operators interacting across four operands)
def pack_flags(data, mask=0xFF, shift=2, fill=0):
    return ((data & mask) >> shift) | ((fill & ~mask) << (8 - shift))
```

Four lines, low CCX. The operator density — `&`, `>>`, `|`, `~`, `<<`, `-` all interacting — is what makes this hard to read and harder to modify safely without introducing a bit-level bug.

**When to raise it:** Numerical or DSL interpreter code where operator density is intrinsic to the domain. Raising to 50 leaves room for legitimate density.

**When to lower it:** Teams that want to catch cognitive density early. D=20 is aggressive but effective.

```toml
[rules.information.difficulty]
threshold = 30
```
