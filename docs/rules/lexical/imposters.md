# lexical.imposters

**What it measures:** Clusters of functions sharing a first
parameter, profiled by multi-signal analysis: body-shape Jaccard
mean, receiver-call density, and modal-token overlap. The profile
classifies each cluster into one of:

- `missing_class` — members actively use the parameter as a
  receiver. Refactor: extract a class.
- `strategy_family` — members are body-shape clones with no
  receiver-call use. Refactor: dispatch table or accept as
  idiomatic free functions. **Do NOT extract a class.**
- `heterogeneous` — cluster real but profile mixed. Review
  before refactoring.
- `infrastructure` / `false_positive` — exempt parameter
  semantics (filesystem paths, third-party types).

**Default threshold:** flag clusters of `≥ 3` functions sharing a
non-trivial first-parameter name. Severity `warning`. Only
`missing_class`, `strategy_family`, and `heterogeneous` profiles
emit violations.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_cluster` | `3` | Minimum cluster size |
| `exempt_names` | `["self", "cls"]` | Parameter names to ignore |

## Profile signals

| Signal | Computation | Means |
|---|---|---|
| `body_jaccard_mean` | mean pairwise Jaccard of cluster members' AST 3-gram body signatures | high → clone family; low → heterogeneous |
| `mean_receiver_calls` | average count of `param.attr` and `param[k]` references per member | high → param treated as receiver |
| `modal_overlap_mean` | average member-name overlap with cluster's modal tokens | high → consistent family naming |

Profile assignment:

- `body_jaccard_mean ≥ 0.7` AND `mean_receiver_calls < 0.5` →
  **strategy_family**
- `mean_receiver_calls ≥ 1.0` → **missing_class**
- otherwise → **heterogeneous**

## Examples

**`color.py: text` cluster** — `red, green, yellow, bold, dim`
all `(text: str) → str`:
- body Jaccard 1.00 (literal Type-2 clones)
- receiver-calls 0.0 (no `text.x` access)
- → `strategy_family`. Advisory says do NOT extract a class;
  consider a dispatch table or accept as idiomatic.

**`output.py: result` cluster** — `format_human, format_quiet,
format_json, _group_by_category, _format_footer` all on
`LintResult`:
- body Jaccard 0.12 (each format does different work)
- receiver-calls 4.4 per member (heavy `result.x` access)
- → `missing_class`. Advisory: extract a class.

## Recursive scoping

Same as `lexical.sprawl` — clusters reported at the narrowest
scope where they cohere (file → package → root). Cross-package
noise (functions sharing `name: str` incidentally) fails the
coherence test.

## Method backing

Per `docs/methods/lexical/multi_criteria_ranking.md` and
`docs/methods/lexical/body_shape_signatures.md`. Citations:

- Tsantalis & Chatzigeorgiou (2009) — multi-criteria refactoring-
  candidate ranking
- Bavota et al. (2010, 2014) — Extract Class via multi-objective
- Roy et al. (2009); Baxter et al. (1998) — Type-2 clone
  detection

## Configuration

```toml
[rules.lexical.imposters]
enabled = true
severity = "warning"
min_cluster = 3
exempt_names = ["self", "cls"]
```

## Why "imposters"

Each parameter looks like an ordinary dependency in its function
signature, but its repeated appearance across N functions reveals
it's actually performing some unifying role. The parameter is
camouflaged.
