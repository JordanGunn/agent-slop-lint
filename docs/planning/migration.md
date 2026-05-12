# Migration approach for v2.0 substrate

Status: hard constraint. The v2.0 substrate (Language,
Codebase, Linter, Slop, views) is built **beside** the
existing code, not as a retrofit. Migration happens one
piece at a time. Old code is deleted only after the new
path is the sole one in use.

Companion docs: `language.md`, `codebase.md`, `linter.md`
lock the target shape this migration moves toward.

## The constraint

No retrofitting. The existing `engine.py`, `_structural/`,
`_lexical/`, `models.py`, and rule modules keep working
unchanged during the migration window. The new substrate
lives in a fresh namespace and grows in parallel.

Three reasons this is non-negotiable:

1. **Parity is testable.** Both linters can run against the
   same corpus and diff their outputs. A retrofit replaces
   the old code in-place, so there is nothing to compare
   "before" against "after."
2. **Reversibility.** If a v2.0 decision proves wrong
   mid-implementation, the old substrate is intact and the
   release can proceed without rollback gymnastics.
3. **Self-application of slop's thesis.** A retrofit is
   exactly the kind of shortcut agentic codebases default to
   (less work, ship faster, accept the half-migrated state).
   Slop exists to surface those shortcuts; the tool's own
   engineering should hold itself to the same bar.

## Stubs first

Before any kernel logic ports across, the full new surface
is defined as stubs: class definitions, method signatures,
record dataclasses, view APIs — bodies empty (`raise
NotImplementedError`) or returning placeholders.

Rationale:

- **Forces the design to stand alone.** If a signature only
  makes sense by reaching into the old implementation, that
  is a signal the new shape is wrong. The stub phase surfaces
  this before behaviour gets ported.
- **Pins the open-round decisions.** Records, `scan()`
  signature, view APIs — these are deferred in the locked
  design docs precisely because they need stress-testing
  against kernel requirements. Writing stubs IS that
  stress-test. Each open round resolves when its stub is
  written and the docs get updated to reflect the resolution.
- **Avoids the "what was the old code doing, let me preserve
  that" trap.** Implementation details that no longer fit the
  new shape are visible as gaps in the stubs, not as
  contamination of the new surface.

## What coexists during migration

| Old | New | Coexistence note |
|---|---|---|
| `engine.py` (`run_lint`) | `linter.py` (`Linter`) | Both importable. CLI uses old until cutover. |
| `models.Violation` | `models.Slop` (or new module) | Result holds both during migration. |
| `models.LintResult` | `Result` (peer to `Linter`) | Same as above. |
| Old rules: `run(root, rc, config)` | New rules: `run(view, rc, config)` | Dual signature in `RuleDefinition`; dispatch flag picks which to call. |
| `_lexical/_words.py` `Lexicon` | New `Lexicon` view under `_corpus/` (or chosen package) | Old keeps serving group-B rules until those rules port. |
| `_structural/`, `_lexical/` kernels | Migrated kernels under the new package | One-at-a-time port; old kernel deleted when no rule references it. |

## Rule-port order

Rules port in this rough order (subject to refinement during
planning):

1. **A simple structural rule first** — e.g. one of the
   complexity rules. Establishes the new view-consumption
   pattern with minimal kernel complexity.
2. **A group-B lexical rule** — `lexical.imposters` or
   `lexical.sprawl`. Exercises the Lexicon slicing API.
3. **Remaining structural rules in dependency order.**
4. **Remaining lexical rules** — including the rest of group
   A, which currently uses `enumerate_functions` directly.
5. **Cross-cutting rules last** — hotspots, dead_code,
   anything that crosses both Structure and Lexicon.

Each port is its own intent. Each intent ends with:

- The new rule is in the registry under the new signature.
- The old rule is removed from the registry.
- Tests pass against the new rule.
- The slop snapshot under `docs/research/snapshots/` is
  updated (or the snapshot tracking the dogfood baseline is
  refreshed) so calibration findings stay comparable.

## Parity gate (before CLI cutover)

The CLI switches from `run_lint(config)` to
`Linter(config).run()` only when:

1. **Every rule has a new-shape implementation.** No rule is
   left on the old `run(root, ...)` signature.
2. **Output parity has been verified.** The new linter
   produces equivalent findings on the dogfood corpus (slop's
   own repo) and on at least one external corpus. Differences
   are explained — e.g. "imposters now uses the multi-signal
   profile, so finding X classified differently is expected."
3. **Performance has been measured.** Wall-clock time on the
   dogfood corpus is recorded. The new linter should be
   meaningfully faster than the old (the consolidation
   argument); if it is not, investigate before cutover.
4. **The JSON output shape has been documented.** Any
   breaking change to consumers (renamed keys, restructured
   shape) is in CHANGELOG and the v2.0 release notes.

Cutover is a single intent. CLI calls the new path; old path
still exists but is unreferenced.

## Deletion is its own final intent

Once cutover is complete and the v2.0 release has shipped,
the old code is removed as a separate, focused intent:

- Delete `engine.py` (the module retires when `linter.py`
  is the only entry point).
- Delete `models.Violation`, `models.LintResult` (replaced
  by `Slop`, `Result`).
- Delete legacy kernel modules under `_structural/`,
  `_lexical/` once no rule references them.
- Delete the dual-signature dispatch in `RuleDefinition`.

This intent is mechanical and reviewable on its own. It
does not bundle with new work. The goal is a clean git
history: design → scaffold → port (N intents) → cutover →
delete.

## What this constraint forbids

For clarity, these moves are explicitly out of scope during
the migration window:

- Editing `engine.py` to "make it more like Linter."
- Editing `models.Violation` to accept new fields meant for
  `Slop`.
- Editing existing kernels to "prepare them for the new
  views."
- Any change to the old substrate that is justified by "this
  will help the v2.0 port."

The discipline is: the old code is frozen except for genuine
bug fixes (which would have happened regardless of v2.0).
Everything else lands on the new substrate.

## Why this lives in its own doc

This constraint cuts across `language.md`, `codebase.md`,
and `linter.md` — none of them is the natural home. It is
also the doc most likely to be referenced when a future
session is about to take a shortcut: "the migration doc
says no retrofitting; pause and verify before editing
`engine.py`." Durable home, focused scope.
