# lexical.stutter

**What it measures:** Identifiers that repeat tokens from their enclosing scope (function, class, or module). A function `read_lidar_data` containing a local `decoded_lidar_data` stutters: `lidar` and `data` are already implied by the surrounding scope.

**Default threshold:** flag any identifier sharing `≥ 2` tokens with its enclosing scope name. Severity `warning`.

**What the numbers mean:** Token overlap is computed after splitting identifiers on snake_case and CamelCase boundaries. A scope-stutter signals that the identifier is leaning on the enclosing context for descriptive content rather than naming the value on its own terms.

## What it prevents

Locals that describe where they live instead of what they are. Every repeated token is noise the reader silently strips before understanding the code.

```python
# ❌ flagged — "user" and "data" are already in the scope name
def process_user_data(raw):
    validated_user_data = validate(raw)
    normalized_user_data = normalize(validated_user_data)
    return normalized_user_data

# ✓ the function name already says "user data"
def process_user_data(raw):
    validated = validate(raw)
    normalized = normalize(validated)
    return normalized
```

**When to raise it:** Codebases with idiomatic prefixing conventions (e.g. ROS-style `lidar_msg_lidar_frame`). Raising to `3` tolerates one shared category token while still flagging deeper repetition.

**When to lower it:** Strict greenfield projects. `min_overlap_tokens = 1` flags every shared token, including small ones like `data` or `info`.

```toml
[rules.lexical.stutter]
min_overlap_tokens = 2
```
