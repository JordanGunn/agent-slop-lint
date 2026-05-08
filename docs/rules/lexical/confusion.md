# lexical.confusion

**What it measures:** Files holding multiple distinct strong-receiver
clusters (per `lexical.imposters`). The file is doing the work of
multiple cohesive units sharing a namespace; the canonical refactor
is to split it along receiver boundaries.

Adapts Lanza & Marinescu's (2006) detection-strategy framework
from class-level (their book targets OO classes) to module-level
(slop's Python corpus is mostly free-function modules).

**Default threshold:** file fires when:
- function count `≥ 5`
- distinct first-parameter clusters of size `≥ 3` count `≥ 2`
- `missing_class`-profile clusters count `≥ 2`

Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_functions` | `5` | Minimum functions in file |
| `min_clusters` | `2` | Minimum distinct first-param clusters |
| `min_cluster_size` | `3` | Minimum members per cluster |
| `min_strong_receivers` | `2` | Minimum `missing_class`-profile clusters |

## What it surfaces

A file with multiple cohesive function families, each clustering
on a different receiver:

```python
# output.py — hypothetical example with multiple strong receivers

def format_human(result): return result.summary
def format_quiet(result): return result.summary
def format_json(result): return result.violations
# ... 5 functions, all using result as a receiver

def render_category(category): return category.name
def aggregate_category(category): return category.violations
def header_extras(category): return category.window
# ... 3+ functions, all using category as a receiver
```

Each cluster is a `missing_class` candidate per `lexical.imposters`.
Two missing-class candidates in one file means the file is doing
the work of two cohesive units. Split it: one module per receiver,
or extract each cluster as a class with its receiver as `self`.

## Method backing

Per `docs/methods/lexical/lanza_marinescu_detection.md`.
Citations:

- Lanza & Marinescu (2006). *Object-Oriented Metrics in Practice.*
  The canonical book for metric-based smell detection;
  Chapter 5 covers Extract Class.
- Marinescu (2004). *Detection Strategies: Metrics-Based Rules
  for Detecting Design Flaws.*

The slop adaptation:
- Lanza/Marinescu use class-level metrics (WMC, TCC, ATFD).
  We use module-level analogues: function count and cluster
  count substitute for class size and class cohesion.
- The strong-receiver gate uses the imposters profile
  (missing_class) rather than attribute-access analysis on
  classes.

## Why this rule is conservative by design

Lanza/Marinescu emphasize that detection strategies should err
toward false-negative over false-positive. A missed bad smell
can be caught later; a false recommendation costs the developer
trust in the tool. This rule's three-AND'd thresholds filter
most incidental cases; it fires only on files where the
multi-receiver pattern is unambiguous.

On slop's own corpus the rule produces zero hits — the imposters
profile is strict enough that most slop files have only one
strong-receiver cluster, which doesn't trigger confusion.

## Configuration

```toml
[rules.lexical.confusion]
enabled = true
severity = "warning"
min_functions = 5
min_clusters = 2
min_cluster_size = 3
min_strong_receivers = 2
```

## Why "confusion"

A reader of a confused file experiences cognitive overload — the
file's lexicon mixes multiple distinct vocabularies that each
deserve their own scope. Naming this rule for the experiential
smell (rather than the mechanical detection criterion) matches
slop's other condition-named rules (`sprawl`, `stutter`,
`tautology`, `verbosity`).
