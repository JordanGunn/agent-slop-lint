# lexical.stutter

**What it measures:** Names that repeat tokens from any enclosing
scope. The hierarchy walked is: package (parent directory) →
module (file stem) → class → function. Two kinds of stutter are
detected:

1. **Entity-name stutter.** A class/function/method NAME stutters
   with one of its enclosing scope names. Example:
   `class UserService: def get_user_service_id(self): ...` — the
   method name itself stutters with the class name.
2. **Identifier stutter.** A local identifier inside a function
   body stutters with one of its enclosing scope names. Example:
   `def check_required_binaries(): required_binaries = [...]` — the
   local repeats the function name's tokens.

Each finding records which scope level (`package` / `module` /
`class` / `function`) triggered it. Per-level toggle parameters
let you dial down specific levels without splitting the rule.

> **v1.2.0 note.** v1.1.x split this into three rules
> (`lexical.stutter.{namespaces, callers, identifiers}`); v1.2.0
> unifies them back into a single hierarchy-aware rule with
> per-level toggles. The split rules' configuration migrates
> automatically via `slop._compat`. The unified rule also catches
> entity-name stutter (method names stuttering with class names),
> a case the split rules missed.

**Default threshold:** flag any name sharing `≥ 2` tokens with
its enclosing scope. Severity `warning`. All four levels enabled
by default.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_overlap_tokens` | `2` | Minimum shared tokens to flag |
| `check_packages` | `true` | Check parent-directory level |
| `check_modules` | `true` | Check file-stem level |
| `check_classes` | `true` | Check enclosing class level |
| `check_functions` | `true` | Check enclosing function level |

## What it catches at each level

### `package` level

```
slop/_lexical/_lexical_helper.py     # _lexical_helper stutters with _lexical
```

### `module` level

```python
# lidar_utils.py
def load():
    lidar_utils_config = {}    # local stutters with module name
    return lidar_utils_config
```

### `class` level (NEW capability — entity-name case)

```python
class UserService:
    def get_user_service_id(self):    # method NAME stutters with class
        ...
```

### `function` level

```python
def check_required_binaries():
    required_binaries = [...]    # local stutters with function name
    for b in required_binaries: ...
```

## Configuration

```toml
[rules.lexical.stutter]
enabled = true
min_overlap_tokens = 2
check_packages = true
check_modules = true
check_classes = true
check_functions = true
severity = "warning"
```

To suppress a specific level (e.g., function-level stutter on a
test corpus where it's expected):

```toml
[rules.lexical.stutter]
check_functions = false
```

## Token comparison is case-insensitive

`UserService` ↔ `user_service_helper` matches correctly. The
v1.0.x kernel was case-sensitive, missing CamelCase ↔ snake_case
stutters; this was fixed in v1.1.0.

## Migration from v1.1.x split rules

Legacy `[rules.lexical.stutter.X]` tables are translated by
`slop._compat`:

```toml
# v1.1.x — three sub-rule tables
[rules.lexical.stutter.namespaces]
min_overlap_tokens = 2

[rules.lexical.stutter.callers]
min_overlap_tokens = 2

[rules.lexical.stutter.identifiers]
severity = "info"
```

…translates to the unified rule's per-level toggles. A consolidated
deprecation notice prints to stderr at config-load time. To migrate
manually, replace the three tables with a single
`[rules.lexical.stutter]` block setting per-level toggles.
