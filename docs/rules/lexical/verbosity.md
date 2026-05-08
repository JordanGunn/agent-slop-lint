# lexical.verbosity

**What it measures:** Function and class names whose own token
count exceeds a threshold. A long entity name compensates for a
missing namespace — `check_required_binaries` is three tokens
because the `Preflight` class it should belong to doesn't exist
yet.

> **v1.2.0 note.** v1.1.x had two verbosity rules:
> `lexical.verbosity` (body identifier mean) and
> `lexical.name_verbosity` (entity name token count). v1.2.0 cut
> the body-mean rule (style measurement, not structural) and
> renamed the entity-name rule to `lexical.verbosity`. Configs
> using `max_mean_tokens = 3.0` against the old rule should
> switch to `max_tokens = 3`.

**Default threshold:** flag function or class names with `> 3`
word-tokens after snake/Camel split. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `max_tokens` | `3` | Maximum allowed word-tokens per function/class name. |
| `check_classes` | `true` | Also check class/struct/interface/trait names. |

## What it surfaces

```python
# ❌ flagged — 5 tokens
def check_required_binaries_for_python_runtime(): ...

# ✓ — 2 tokens
def check_runtime(): ...

# ✓ — same logic in a class
class PythonRuntime:
    def check(self): ...
```

A 4+ token function name almost always means the function is
doing class-level work without a class. The function name
re-creates the namespace inline. The fix is rarely "rename" — it's
"extract the abstraction the name is begging for."

## Configuration

```toml
[rules.lexical.verbosity]
enabled = true
severity = "warning"
max_tokens = 3
check_classes = true
```

## Why this is structural

Body-identifier verbosity (the cut v1.1.x rule) is a style
measurement — long local names are a readability concern but
don't indicate structural debt. Entity-name verbosity is
structural — long names on functions and classes signal a
missing namespace or class. Slop v1.2.0 ships only the
structural variant.
