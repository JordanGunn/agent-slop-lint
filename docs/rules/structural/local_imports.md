# structural.local_imports

**What it measures:** Import statements whose nearest enclosing AST ancestor is a function or method definition. Function-scoped imports are invisible to `structural.deps` (which walks only module-level imports), impose repeated import-machinery cost on every call, and scatter the dependency surface across the call graph rather than the file boundary.

**Default:** flag any local import. Severity `warning`.

**Languages:** Python and Julia (AST tier, full ancestor traversal); Rust (text tier, indentation heuristic). Other languages are silently skipped.

## What it prevents

An import buried in a function body, invisible to the dependency graph and re-executed on every call.

```python
# ❌ flagged
def process_record(record):
    import re    # import machinery runs on every call
    import json  # invisible to structural.deps
    return json.loads(re.sub(r"\s+", " ", record))

# ✓ move imports to the top of the file
import re
import json

def process_record(record):
    return json.loads(re.sub(r"\s+", " ", record))
```

**When to raise it:** Codebases that legitimately use conditional or optional-dependency imports inside functions. Setting `threshold = N` tolerates up to N local imports per file; the more common pattern is to leave the threshold at 0 and waive the legitimate exceptions per-file via `[[waivers]]`.

**When to disable:** Rare. The advisory severity already lets the rule report without failing; turning it off entirely loses the signal that local imports were introduced.

```toml
[rules.structural.local_imports]
threshold = 0
severity = "warning"
```
