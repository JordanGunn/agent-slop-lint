# lexical.identifier_singletons

**What it measures:** Functions where most named locals are bound and
then referenced exactly once. The agent reflex of giving every
intermediate value its own name "in case it's needed later" produces
a chain of fresh names that don't accumulate meaning.

**Default threshold:** flag functions with `≥ 4` local bindings where
more than `60%` of those bindings are written-once-read-once
(excluding bindings that ARE the return value). Severity `info`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_locals` | `4` | Minimum bindings before the function is analyzed. |
| `max_singleton_fraction` | `0.6` | Fraction of singletons-vs-locals that triggers a flag. |

## What it surfaces

```python
# ❌ flagged
def process(req):
    parsed = parse(req)
    user_id = parsed.id
    record = lookup(user_id)
    audit_entry = build_log(record)
    payload = build_response(record)
    write_audit(audit_entry)
    return payload
# Six fresh names, four used exactly once.

# ✓ — same logic, names accumulate meaning through reference
def process(req):
    user = lookup(parse(req).id)
    write_audit(build_log(user))
    return build_response(user)
```

## What it ignores

- The singleton local that IS the return value (`x = compute();
  return x` is fine).
- Functions with fewer than `min_locals` bindings (small functions
  legitimately use one-shot names).
- Augmented assignments (`+=`, `-=`) — these aren't bindings.
- Bindings beginning with `_` (leading-underscore convention for
  "I know this is unused").

## Scope

Initial implementation covers Python only — Python has the cleanest
binding semantics (assignment statement = local binding). Other
languages need per-language handling for `let`/`var`/`const` and
that's a deliberate follow-up.

## Severity

This rule defaults to `info` rather than `warning`. The signal is
real but the per-instance impact is low — it's a soft signal worth
reviewing in aggregate, not a fail-the-build smell.

```toml
[rules.lexical.identifier_singletons]
enabled = true
severity = "info"
min_locals = 4
max_singleton_fraction = 0.6
```
