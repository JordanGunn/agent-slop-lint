# structural.redundancy

**What it measures:** Pairs of sibling top-level functions in a single file that share a significant number of non-trivial callee names. When two peer functions both call the same set of helpers, it is likely that either a new shared helper should extract the common calls, or one function is a partial copy of the other with only minor variation (poor factoring).

**Default threshold:** flag pairs sharing `≥ 3` non-trivial callees with overlap score `≥ 0.5`. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_shared` | `3` | Minimum number of shared non-trivial callees to flag a pair. |
| `min_score` | `0.5` | Minimum `\|shared\| / max(\|callees_a\|, \|callees_b\|)` to flag a pair. |

## What it prevents

Two functions that look different on the surface but call the same helpers in the same order. The shared setup hasn't been extracted yet — and when the shared logic needs to change, it has to be found and updated in both places.

```python
# ❌ flagged — 3 shared callees: validate_schema, normalize_rows, build_header
def export_csv(data):
    data = validate_schema(data)
    data = normalize_rows(data)
    header = build_header(data)
    return render_csv(data, header)

def export_json(data):
    data = validate_schema(data)
    data = normalize_rows(data)
    header = build_header(data)
    return render_json(data, header)

# ✓ extract the shared setup
def _prepare(data):
    return normalize_rows(validate_schema(data)), build_header(data)
```

**When to raise it:** Codebases with many small dispatchers that legitimately share helper sets. Setting `min_shared = 5` cuts down noise significantly.

> **Test-suite noise.** Every test function in a module calls the same setup helpers (`_rc()`, `write_text()`, `load_config()`, …). With the default `min_shared = 3`, a test file with 20 test functions easily generates hundreds of advisory pairs. If your test suite drowns the output, raise `min_shared` to 5–6 in your `.slop.toml`, or add your test directory to the global `exclude` list.

**When to lower it:** Greenfield projects where you want to catch nascent duplication early. `min_shared = 2` flags more aggressively.

```toml
[rules.structural.redundancy]
min_shared = 3
min_score = 0.5
severity = "warning"
```
