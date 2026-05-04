# structural.orphans

**What it measures:** Unreferenced symbols (functions, classes, constants) — dead code candidates. Uses tree-sitter for definition detection and ripgrep for reference counting.

**Default:** Disabled. This is advisory, not a gate.

## What it prevents

Dead code that still looks alive. Functions nobody calls, still being maintained, still showing up in searches, still occupying mental space when reading the file.

```python
# ❌ flagged — nothing in the codebase references this
def generate_legacy_pdf_report(data):
    ...  # 80 lines

# grep -r "generate_legacy_pdf_report" .  →  0 results
```

**Why it's off by default:** False positives are common. Symbols may be referenced by:
- Dynamic dispatch (`getattr`, reflection)
- String-based lookups (ORMs, serializers)
- External consumers (public API, CLI entry points)
- Test fixtures

**When to enable:** Periodic cleanup audits. Enable, review the output, delete what's clearly dead, then disable again. Don't leave it on as a CI gate — the false positive rate will erode trust.

**Confidence levels:**
- `"high"` — only flag symbols with zero textual references anywhere in the codebase. Safest.
- `"medium"` — include symbols with very few references (may be test-only). More aggressive.

```toml
[rules.structural.orphans]
enabled = true            # for cleanup audits
min_confidence = "high"
severity = "warning"
```
