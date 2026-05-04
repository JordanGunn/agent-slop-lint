# structural.complexity.cognitive

**What it measures:** Campbell's Cognitive Complexity (2018) — a proxy for how hard a function is to *read*, not just how many paths it has. Nesting adds exponential penalty; boolean operator sequences are collapsed (three `&&` in a row count as one increment, not three).

**Default threshold:** `CogC > 15`

**What the numbers mean:** CogC tracks reading difficulty more closely than CCX. A deeply nested function with CCX=8 might have CogC=20 because the nesting penalty compounds. Conversely, a flat function with many sequential branches might have CCX=15 but CogC=10.

## What it prevents

Deep nesting that forces readers to juggle context at every level. Each new indent is a "remember this when you come back out" tax. By the time you reach the innermost block, you've lost the thread.

```python
# ❌ flagged (CogC ≈ 22 — nesting penalty compounds)
def sync_records(records, config):
    for record in records:
        if config.enabled:
            if not record.deleted:
                for target in config.targets:
                    if target.accepts(record.type):
                        try:
                            target.push(record)
                        except TimeoutError:
                            if config.retry:
                                retry_queue.add(record)
```

**When to raise it:** Codebases with complex but well-structured branching (e.g., parsers, state machines). Raising to 20–25 lets structured complexity through while still catching spaghetti.

**When to lower it:** Teams where readability is the primary concern. 10 is aggressive but effective.

```toml
[rules.structural.complexity]
cognitive_threshold = 15
```
