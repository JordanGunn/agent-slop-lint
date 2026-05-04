# structural.god_module

**What it measures:** Number of top-level callable definitions (functions plus classes) per file. A file that defines many unrelated top-level symbols is a god module — it resists focused ownership, makes test isolation expensive, and forces every reader to skim the whole file to understand its scope. The metric is a count, not a complexity; it captures breadth, not depth.

**Default threshold:** `> 20` top-level definitions. Severity `warning`.

## What it prevents

The file that became the project's junk drawer. Everything loosely related to "users" or "utilities" accumulates here until nobody knows what's in it without reading the whole thing.

```python
# ❌ flagged — utils.py, 35 top-level definitions
def format_date(d): ...
def parse_phone(s): ...
def send_email(to, body): ...
def hash_password(pw): ...
def load_config(path): ...
def validate_uuid(s): ...
def resize_image(img, w, h): ...
# … 28 more unrelated functions
```

**When to raise it:** Codebases with many small symbol-bag modules that legitimately collect related primitives (constants, dataclasses, enums grouped by domain). Raising to 30–40 accommodates this.

**When to lower it:** Projects that enforce one-class-per-file or one-feature-per-file conventions. `threshold = 10` catches drift early.

```toml
[rules.structural.god_module]
threshold = 20
severity = "warning"
```
