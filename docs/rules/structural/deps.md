# structural.deps

**What it measures:** Dependency cycles between modules. The Acyclic Dependencies Principle (Lakos 1996; Martin 2002) holds that cycles prevent independent reasoning, testing, and extraction of any module in the cycle — every change touches the whole loop. slop detects them with Tarjan's (1972) SCC algorithm on the import graph.

**Default:** Fail on any cycle.

## What it prevents

Import cycles that make it impossible to test or import any module in the loop in isolation — loading one drags in the whole cycle.

```python
# ❌ flagged — cycle: models → services → models

# models.py
from services import get_user_status  # needs services

# services.py
from models import User               # needs models
# → ImportError or silent partial initialisation at runtime
```

**When to disable:** Very early-stage prototypes where module boundaries are still forming. Re-enable as soon as the structure stabilizes — cycles that form early tend to calcify.

```toml
[rules.structural.deps]
fail_on_cycles = true
```
