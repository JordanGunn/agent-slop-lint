# Documentation

slop implements a set of well-cited software engineering metrics (McCabe
1976 through Campbell 2018) as a deterministic linter. Rules fire on
static properties of the code, not on anyone's opinion of it.

## Use it

- [SETUP.md](SETUP.md) — install, wire up CI, install the git pre-commit
  hook, install the bundled agent skill.
- [CONFIG.md](CONFIG.md) — per-rule threshold tuning, profile presets
  (`default`, `lax`, `strict`), scoped waivers, and the rationale for the
  defaults that diverge from the original papers.
- [rules/README.md](rules/README.md) — the authoritative rule index. Every
  rule has its own page under `rules/{structural,information,lexical}/`.
- [JULIA.md](JULIA.md) — Julia language status, deferrals, and calibration
  notes.

## Why these metrics

- [philosophy/why-slop-exists.md](philosophy/why-slop-exists.md) — why
  automated quantitative signals matter more as agents write more code.
- [philosophy/the-defensible-subset.md](philosophy/the-defensible-subset.md)
  — which metrics slop implements and the five criteria each one satisfies.
- [philosophy/why-external-metrics.md](philosophy/why-external-metrics.md)
  — why the checks run outside the agent's own reasoning rather than as
  self-assessment.
- [philosophy/the-ceremonial-reviewer.md](philosophy/the-ceremonial-reviewer.md)
  — what happens when the only reviewer is a rubber stamp, and how
  external metrics compensate.
- [philosophy/artifact-proxies.md](philosophy/artifact-proxies.md) —
  evidence model for artifact-derived information, lexical, and semantic
  proxies.
- [philosophy/references.md](philosophy/references.md) — full bibliography.

## Rule families at a glance

slop ships 25 rules across three suites separated by measurement
substrate. The full per-rule index lives in
[rules/README.md](rules/README.md).

| Suite | Group | Primary sources |
|---|---|---|
| `structural.complexity` | `cyclomatic`, `cognitive`, `npath` | McCabe 1976, Campbell 2018, Nejmeh 1988 |
| `structural.class` | `complexity`, `coupling`, `inheritance.depth`, `inheritance.children` | Chidamber & Kemerer 1994 |
| `structural.types` | `sentinels`, `hidden_mutators`, `escape_hatches` | type-discipline rules |
| `structural.{hotspots,packages,deps}` | per-file churn, package distance, cycle detection | Tornhill 2015, Martin 1994/2002, Lakos 1996, Tarjan 1972 |
| `structural.{duplication,god_module,local_imports,redundancy,orphans}` | shape and concentration rules | widely tooled |
| `information.{volume,difficulty}` | per-function information density | Halstead 1977 |
| `information.{magic_literals,section_comments}` | inline density signals | — |
| `lexical.{stutter,verbosity,tersity}` | identifier vocabulary discipline | — |

Every cited source has a full bibliographic entry in
[philosophy/references.md](philosophy/references.md), with a pointer to the
slop rule it backs.
