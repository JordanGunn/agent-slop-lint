# information.section_comments

**What it measures:** Number of divider-style comments used as section markers inside a function body (e.g. `# --- parsing ---`, `// ===== validation =====`). A function with more than `threshold` section dividers is doing too many conceptually distinct things; each divider is a signal for "extract a helper function here."

**Default threshold:** `> 2` section dividers per function. Severity `warning`.

## What it prevents

A function that secretly contains three smaller functions, separated by divider comments because the author knew the phases were distinct but didn't extract them.

```python
# ❌ flagged (3 section dividers = 3 functions waiting to be extracted)
def handle_request(request):
    # --- parse ---
    body    = json.loads(request.body)
    user_id = body["user_id"]

    # --- validate ---
    if user_id not in active_users:
        raise ValueError("unknown user")

    # --- persist ---
    db.save({"user_id": user_id, "ts": now()})
    return {"ok": True}

# ✓
def parse_request(request): ...
def validate_user(user_id): ...
def persist_event(user_id): ...
```

**When to raise it:** Codebases where divider comments are used as documentation rather than conceptual breaks. Raising to 4–5 reduces noise.

**When to lower it:** Greenfield projects aiming for single-responsibility functions. `threshold = 1` flags any function that needed a divider.

```toml
[rules.information.section_comments]
threshold = 2
severity = "warning"
```
