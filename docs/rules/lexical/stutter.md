# lexical.stutter.* (split)

**What it measures:** Identifiers that repeat tokens from their
enclosing scope. A v1.0.x dogfood pass found that the unified
`lexical.stutter` rule conflated three different smells with very
different per-instance impact, and users were writing waivers to dial
down the variant they didn't care about. v1.1.0 splits the rule into
three so each can be configured independently.

| Rule | Scope | Default severity | Catches |
|---|---|---|---|
| `lexical.stutter.namespaces` | module | `warning` | symbol stutters with module path |
| `lexical.stutter.callers` | class | `warning` | method/attribute stutters with class |
| `lexical.stutter.identifiers` | function | `info` | local variable stutters with function name |

All three rules share one detection kernel; they differ only in which
enclosing-scope kind counts as a stutter source. Token comparison is
case-insensitive (so `UserService` ↔ `user_service_helper` matches
correctly).

**Default threshold:** flag any identifier sharing `≥ 2` tokens with
the configured enclosing-scope name.

**Settings (per rule):**

| Setting | Default | Description |
|---|---|---|
| `min_overlap_tokens` | `2` | Minimum number of shared tokens required to flag. |

## What each rule catches

### `lexical.stutter.namespaces`

The module path is its own form of namespace. Symbols whose own
tokens recapitulate the module path are leaning on the path for
descriptive content.

```python
# slop/rules/complexity.py
# ❌ flagged — `complexity_kernel` repeats the module name
def complexity_kernel(...): ...

# ✓ — module path already says "rules.complexity"
def kernel(...): ...
```

Highest signal-to-noise of the three; the module already names the
thing.

### `lexical.stutter.callers`

Method and attribute names that repeat tokens from their enclosing
class. The strongest agent tell of the three — agents producing
`UserService.get_user_user_id` is a recognisable failure mode.

```python
# ❌ flagged
class UserService:
    def get_user_id(self): ...    # `user` already in class name

# ✓
class UserService:
    def get_id(self): ...
```

### `lexical.stutter.identifiers`

Local variable names that stutter with the enclosing function. Lower
per-instance impact but high frequency. Default severity `info` to
keep the noise floor manageable.

```python
# ❌ flagged
def check_required_binaries():
    required_binaries = [...]    # everything in the function is about required binaries
    for b in required_binaries: ...

# ✓
def check_required_binaries():
    targets = [...]
    for b in targets: ...
```

## Migration from `lexical.stutter`

Legacy `lexical.stutter` rule references and `[rules.lexical.stutter]`
TOML tables are translated automatically:

- The rule name `lexical.stutter` → `lexical.stutter.identifiers`
  (the closest single-rule successor based on what the original rule
  fired on most often in practice).
- The TOML table `[rules.lexical.stutter]` → migrates its keys
  to `[rules.lexical.stutter.identifiers]`. Existing waivers and
  `min_overlap_tokens` settings keep working without edits.

A consolidated deprecation notice prints to stderr at config-load
time. To migrate cleanly, replace `lexical.stutter` with the
specific rule name you want. If you want all three modes back, list
all three.

```toml
# legacy (still works via compat shim, prints deprecation)
[rules.lexical.stutter]
min_overlap_tokens = 2

# canonical (preferred)
[rules.lexical.stutter.namespaces]
min_overlap_tokens = 2

[rules.lexical.stutter.callers]
min_overlap_tokens = 2

[rules.lexical.stutter.identifiers]
severity = "info"
min_overlap_tokens = 2
```
