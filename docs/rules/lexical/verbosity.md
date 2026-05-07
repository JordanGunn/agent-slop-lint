# lexical.name_verbosity

**What it measures:** Function and class names whose own token count
exceeds a threshold. Independent from `lexical.verbosity` (which
measures the verbosity of *body* identifiers). A long function name is
usually a class-without-class symptom: `check_required_binaries` is
three tokens because the namespace it should belong to doesn't exist
yet.

**Default threshold:** flag function or class names with `> 3` word-
tokens after snake/Camel split. Severity `warning`.

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

A 4+ token function name almost always means the function is doing
class-level work without a class. The function name re-creates the
namespace inline. The fix is rarely "rename"; it's "extract the
abstraction the name is begging for."

## When to lower it

Greenfield projects, or codebases where function names already trend
short — `max_tokens = 2` flags more aggressively.

## When to raise it

DDD-style codebases with intentionally long behaviour-describing names.
Setting `max_tokens = 4` or `5` reduces noise without disabling the
rule.

```toml
[rules.lexical.name_verbosity]
enabled = true
severity = "warning"
max_tokens = 3
check_classes = true
```
