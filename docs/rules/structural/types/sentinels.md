# structural.types.sentinels

**What it measures:** Function parameters annotated `str` whose names match a sentinel pattern (`status`, `mode`, `kind`, `type`, `state`, …) and whose call-site literal cardinality is bounded. These are stringly-typed parameters: the caller must know a magic string constant from memory or documentation. Python's `Literal[...]` and `enum.Enum` both solve this while remaining runtime-compatible.

**Default threshold:** flag entries with call-site literal cardinality `≤ 8`. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `max_cardinality` | `8` | Flag entries where call-site literal cardinality ≤ this value. Set to `0` to flag all sentinel-named `str` params regardless of call sites. |
| `require_str_annotation` | `true` | Only flag params with explicit `str` annotation. |

## What it prevents

A string parameter that's secretly an enum. The valid values live in documentation or the caller's memory. Typos and wrong capitalisation silently succeed at runtime.

```python
# ❌ flagged
def send_notification(user, channel: str):
    ...  # valid values: "email", "sms", "push" — caller has to just know

send_notification(user, "Email")   # wrong case — silently does nothing
send_notification(user, "e-mail")  # typo     — silently does nothing
send_notification(user, "slack")   # unknown  — silently does nothing

# ✓
from typing import Literal

def send_notification(user, channel: Literal["email", "sms", "push"]):
    ...  # the type checker now catches all three mistakes above
```

**When to raise it:** Domains where parameters legitimately accept many distinct strings (e.g., MIME types, locale codes). Raising to 16–32 reduces noise.

**When to lower it:** Greenfield projects pushing for `Literal`/`Enum` discipline. Setting `max_cardinality = 0` flags every sentinel-named `str` parameter.

```toml
[rules.structural.types.sentinels]
max_cardinality = 8
require_str_annotation = true
severity = "warning"
```
