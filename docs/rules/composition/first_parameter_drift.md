# composition.first_parameter_drift

**What it measures:** Groups of free functions sharing a
first-parameter name (`def render(canvas)`, `def transform(canvas,
…)`, `def serialize(canvas) -> str`). When `n` functions all take
`canvas` as their first argument, the canvas is acting as a
de facto receiver — and the `n` functions are de facto methods on
a missing class.

**Default threshold:** flag clusters of size `≥ 3` not in the
exempt list. Severity `warning`. Only **strong** clusters generate
violations; **weak** and **false-positive** clusters appear in
the summary but don't fail the run.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_cluster` | `3` | Minimum number of functions sharing a first-parameter name. |
| `exempt_names` | `["self", "cls"]` | Parameter names to ignore. Add domain-specific terms like `"node"`, `"path"`, `"tree"` if they generate noise. |

## What it surfaces

```python
# ❌ flagged — 3 functions take `canvas` as first parameter
def render(canvas): ...
def transform(canvas, matrix): ...
def serialize(canvas) -> str: ...

# Candidate refactor:
class Canvas:
    def render(self): ...
    def transform(self, matrix): ...
    def serialize(self) -> str: ...
```

## Verdict classification

Not every shared-first-parameter cluster is a missing class. The
kernel classifies each cluster:

- **strong** — domain noun, multi-word verbs, no obvious framework
  affiliation. These generate violations.
- **weak** — generic infrastructure name (`root: Path`, `config:
  dict`). The pattern is real but the refactor is unlikely to be
  worth it. Reported in the summary, no violation.
- **false_positive** — third-party library type (`node`, `tree`,
  `ctx`). The "class" already exists upstream; what the user has
  is a perfectly normal helper family over an external type. No
  violation.

The classifier is a heuristic, not a proof. Override with
`exempt_names` for domain-specific noise.

```toml
[rules.composition.first_parameter_drift]
min_cluster = 3
exempt_names = ["self", "cls", "node", "tree"]
severity = "warning"
```

## When to act

Strong clusters are the most actionable signal in the composition
suite. If you have five functions all taking `order` as their
first parameter, you have an `Order` class hiding in plain sight.
The classification machinery exists specifically to keep the
signal-to-noise ratio high enough that strong clusters are worth
acting on by default.

## Prior art

- Bavota et al. *Methodbook* / Extract Class refactoring detection
  family — the canonical "find a hidden class" research line.
  This rule's signal is a lighter-weight variant: shared
  first-parameter name as a proxy for shared receiver-of-method.
- Fowler (1999/2018). *Refactoring*. The Move Method and Extract
  Class catalog entries describe the target refactor when this
  rule fires.

See [`docs/philosophy/composition-and-lexical.md`](../../philosophy/composition-and-lexical.md)
for the methodology walkthrough.
