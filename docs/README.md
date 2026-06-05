# Documentation

slop implements a set of well-cited software-engineering metrics (McCabe 1976 through
Campbell 2018) as a deterministic linter. Rules fire on static properties of the code, not
on anyone's opinion of it — and each finding is a verdict the agent can act on or evidence
it should investigate.

## Use it

- [rules/README.md](rules/README.md) — the 25 rules at a glance. The always-current
  reference is `slop rules` (listing) and `slop schema` (config shape); each rule's full
  rationale lives in its module docstring under `src/slop/rules/`.
- [CONFIG.md](CONFIG.md) — `.slop.toml` / `[tool.slop]`: per-rule thresholds keyed by
  altitude, and scope-keyed `[ignore]` exemptions.
- Install and CLI usage are in the repo-root [README](../README.md).

## How it's built

The architecture (the Corpus › Realm › Package › Module › Class › Callable component model,
the `Structure` / `Lexical` views, the dispatcher, the finding ontology) is documented for
contributors in the repo-root [CLAUDE.md](../CLAUDE.md). Durable internal design docs live
under `docs/.internal/design/`.

## Why these metrics

- [philosophy/why-slop-exists.md](philosophy/why-slop-exists.md) — why quantitative signals
  matter more as agents write more code.
- [philosophy/the-defensible-subset.md](philosophy/the-defensible-subset.md) — which
  metrics slop implements and the criteria each satisfies.
- [philosophy/why-external-metrics.md](philosophy/why-external-metrics.md) — why the checks
  run outside the agent's own reasoning.
- [philosophy/the-ceremonial-reviewer.md](philosophy/the-ceremonial-reviewer.md) — what
  happens when the only reviewer is a rubber stamp.
- [philosophy/artifact-proxies.md](philosophy/artifact-proxies.md) — the evidence model for
  artifact-derived, lexical, and semantic proxies.
- [philosophy/references.md](philosophy/references.md) — full bibliography.

The philosophy essays are durable design rationale; where they name a specific rule, treat
`slop rules` as the current source of truth (the rule set evolved in the v3 rebuild).
