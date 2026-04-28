# Documentation

slop implements a set of well-cited software engineering metrics (McCabe
1976 through Campbell 2018) as a deterministic linter. The rules fire on
static properties of the code, not on anyone's opinion of it. The full
rationale, references, and worked examples live in the files linked below.

## Start here

If you want to understand why slop exists and why these specific metrics:

- [philosophy/why-slop-exists.md](philosophy/why-slop-exists.md): why
  automated quantitative signals matter more as agents write more code.
- [philosophy/the-defensible-subset.md](philosophy/the-defensible-subset.md):
  which metrics slop implements and the five criteria each one satisfies.
- [philosophy/why-external-metrics.md](philosophy/why-external-metrics.md):
  why the checks run outside the agent's own reasoning rather than as
  self-assessment.
- [philosophy/the-ceremonial-reviewer.md](philosophy/the-ceremonial-reviewer.md):
  what happens when the only reviewer is a rubber stamp, and how external
  metrics compensate.
- [philosophy/artifact-proxies.md](philosophy/artifact-proxies.md):
  future-facing evidence model for artifact-derived comprehension, lexical,
  and semantic proxies.
- [philosophy/references.md](philosophy/references.md): full bibliography.

## Use it

- [SETUP.md](SETUP.md): install, wire up CI, install the git pre-commit
  hook.
- [CONFIG.md](CONFIG.md): per-rule threshold tuning, profile presets
  (`default`, `lax`, `strict`), and the rationale for the three defaults
  that diverge from the original papers.

## What it found on its own source

slop was pointed at its own codebase under default thresholds. The result
was ten violations across four functions. The two posts below show the raw
report and the refactor that cleared it.

- [before.md](before.md): the raw report, with the actual code that was
  flagged. Three metrics (cyclomatic, Halstead, NPath) converged on the
  engine's main loop from different angles.
- [after.md](after.md): the refactor, with before/after code snippets
  and the full delta table. `cli.main` NPath went from 1024 to 8. The
  headline number is the 128× reduction, but the more interesting part
  is that none of the refactors were clever; the metrics just pointed at
  things nobody had noticed during ordinary review.
- [dogfood-deps-kernel.md](dogfood-deps-kernel.md): a later dogfood case
  study showing how the former AUx `deps_kernel` scored when kernel
  exclusions were removed, why the finding was valid, and what corrective
  course was selected.

## What rules exist

The authoritative rules table with default thresholds and primary sources
lives in the [main README](../README.md). Brief grouping by metric family:

| Family | Rules | Primary sources |
|---|---|---|
| complexity | `cyclomatic`, `cognitive`, `weighted` | McCabe 1976, Campbell 2018, Chidamber & Kemerer 1994 |
| halstead | `volume`, `difficulty` | Halstead 1977 |
| npath | `npath` | Nejmeh 1988 |
| hotspots | `hotspots` | Tornhill 2015 |
| packages | `packages` (Distance from the Main Sequence) | Martin 1994, 2002 |
| deps | `deps` (Acyclic Dependencies Principle) | Lakos 1996, Martin 2002 |
| class | `coupling`, `inheritance.depth`, `inheritance.children` | Chidamber & Kemerer 1994 |
| orphans | `orphans` (advisory, disabled by default) | widely tooled |

Every source above has a full bibliographic entry in
[philosophy/references.md](philosophy/references.md), with a pointer to
the slop rule it backs.
