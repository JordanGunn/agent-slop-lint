# lexical.slackers

**What it measures:** Real first-parameter clusters (per
`lexical.imposters`) whose member function names refuse to follow
any common naming template. The cluster IS structurally
meaningful — the names just slack on expressing it.

**Default threshold:** flag clusters with within-cluster affix
coverage `≤ 30%` AND profile is `missing_class` or
`heterogeneous`. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_cluster` | `3` | Minimum cluster size |
| `exempt_names` | `["self", "cls"]` | Parameter names to ignore |
| `max_coverage` | `0.30` | Below this coverage, the cluster fires |

## What it surfaces

Functions that share a meaningful receiver but whose names don't
admit it:

```python
def calculate_invoice_total(customer):
    return customer.lines

def determine_eligibility(customer):
    return customer.tier

def serialize_for_audit(customer):
    return customer.id

def fetch_account_history(customer):
    return customer.id
```

Five functions share `customer` and use it as a receiver
(`customer.x` accesses → imposters profile = `missing_class`).
But the names follow no template: different verbs, different
shapes, no common token covers more than one. Affix coverage is
0%.

The smell is "the family relationship is invisible from the
outside." A reader scanning these names sees four unrelated
functions; only the parameter signatures reveal the kinship.

## Why this is distinct from sprawl

`lexical.sprawl` fires on *templated* naming where the closed
alphabet is *present* (`format_human, format_quiet, format_json`).
`lexical.slackers` fires on the *absence* of a template where one
would express a real cluster.

The two rules detect opposite ends of the same dimension —
present vs absent template — applied to different cluster
shapes (alphabet sprawl vs first-parameter cluster).

## Why not the strategy_family profile

When the imposters profile is `strategy_family` (e.g., `color.py`
red/green/yellow/bold/dim), the absence of a verb template is
intentional — each name IS its alphabet member. Flagging this
under slackers would be wrong. The rule explicitly excludes
strategy_family clusters.

## Method backing

Per `docs/methods/lexical/within_cluster_affix.md`. Reuses the
affix-pattern primitive from `lexical.sprawl` at finer scope
(within a single first-parameter cluster's member names).

## Configuration

```toml
[rules.lexical.slackers]
enabled = true
severity = "warning"
min_cluster = 3
exempt_names = ["self", "cls"]
max_coverage = 0.30
```

## Why "slackers"

The cluster's members slack on naming. The class they belong to
is unrealized, AND the names don't even bother to indicate the
kinship. Members refuse to align with each other. Pairs tonally
with `imposters` (active deception) as the passive-negligence
counterpart.

## What an agent can fix

Slackers is one of the higher-actionable rules — fixing it is
mechanical. Pick a template (`verb_param_X`, `param_attribute`,
etc.), apply across cluster members. The structural refactor
(class extraction) can follow or be deferred; the rename alone
makes the cluster legible.
