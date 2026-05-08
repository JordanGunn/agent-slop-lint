# slop v1.2.0 dogfood snapshot

Frozen copy of the slop package at v1.2.0, kept as a stable
observational corpus for calibration work. The repo's
`.slop.toml` points at this directory as its dogfood target —
so `slop lint` from the repo root reproduces these numbers
deterministically while the live `src/` tree continues to evolve.

## Provenance

| Field | Value |
|---|---|
| Date captured | 2026-05-08 |
| Git SHA | `33e05dff8711272cea6a2343cc655cb8b7595434` |
| Short SHA | `33e05df` |
| Branch | `feature/v1.1.0-composition-and-lexical` (contents are v1.2.0; branch name predates the rename) |
| Package version | `1.2.0` |
| Source path | `src/cli/slop/` (vendored to `slop/` here) |
| Files | 78 Python files |
| Size | ~970 KB |

## Headline dogfood numbers

From `slop lint` against this snapshot, using the repo's
`.slop.toml` (kernel subpackages excluded, hotspots and packages
disabled, waivers applied). Full per-violation detail in
`dogfood.json`.

```
rules_checked:   28
rules_skipped:    3
violation_count: 40
advisory_count:  38
waived_count:    52
result:          fail
```

Per-rule violation counts (rules that fired):

```
structural.complexity.cyclomatic    13
structural.complexity.cognitive     14
structural.complexity.npath          6
structural.redundancy                5
structural.types.sentinels           2
structural.types.hidden_mutators     3
structural.duplication               2
information.volume                   4
information.difficulty               3
lexical.stutter                      9
lexical.cowards                      1
lexical.imposters                   11
lexical.slackers                     5
```

Rules with zero violations are still in the run (silent passes,
not skipped). Skipped rules: `structural.hotspots` (no git
history in the snapshot), `structural.packages` (disabled in
config), `structural.orphans` (skip reason recorded in
dogfood.json).

## Why this snapshot exists

Slop's empirical thesis (catching what humans let pass in
agent-generated code) is anchored in dogfood numbers. As the
live `src/` tree evolves through v2.0+ work, those numbers drift.
The snapshot:

- Preserves the v1.2.0 numbers as a reproducible reference.
- Provides a stable target for before/after diffs when rule
  kernels or stop-word lists change. Phase 05 (lexicon hygiene)
  measures its impact against this snapshot.
- Acts as one observational data point alongside the labelled
  smell fixtures planned in Phase 06. Snapshots are *unlabelled*
  full-codebase corpora; smell fixtures are *labelled* small
  examples. Both are needed.

## How to use

The repo config is wired up. From the repo root:

```bash
uv run slop lint                            # lints this snapshot
uv run slop check lexical.imposters         # any single rule
```

To lint live development code instead:

```bash
uv run slop lint --root src/cli/slop
```

## Maintenance

- Refresh the snapshot at major version changes (`v1.3.0`,
  `v2.0`, ...) by creating a new sibling directory and pointing
  the repo `.slop.toml` `root` at it. Do not overwrite this one.
- If the duplication becomes painful, migrate snapshots to a
  git-tag-plus-script approach (tag the SHA, materialise via
  `git archive` on demand). Acceptable to defer while iteration
  is heavy.
