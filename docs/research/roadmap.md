# Research roadmap — pause point + open threads

**Snapshot taken:** 2026-05-18, after obs 09 + snapshot rename.

## Where we are

The lexical-signal diagnostic suite is built. Two layers exist:

- **Layer 1 (named rules)** — 9 lexical rules that emit violations: stutter, verbosity, cowards, hammers, tautology, sprawl, imposters, slackers, confusion. Each fires on a specific known pattern. CI-grade, has thresholds, severity, waivers.
- **Layer 2 (diagnostic primitives)** — distribution-shape instrumentation: `frequencies`, `modal_tokens`, `alphabet`, `coverage`, `overlap`, `token_locations`, `body_token_locations`, `callable_token_bags`, `file_token_bags`, `cooccurrences`, `packets`, `by_file`, `by_package`, `hapax_ratio`, `frequency_head`, `spread_dominant`, `middle_spread`, `packet_isolates`. Plus the class-ownership filter (`Structure.class_vocabularies` + `split_packets_by_class_ownership`), the corrective-action mapper (`map_packets_to_actions`), the rule×cell cross-tab (`violations_with_cells` + matrix formatters).

Both layers exercise against the v1.2.0 snapshot (now underscore-renamed) and the current dev tree. 590 tests pass. Nine observation documents under `docs/research/observations/`, with JSON data dumps under `docs/research/observations/data/`.

## The current pivot (2026-05-18)

We're pausing the diagnostic build-out to **shape the current dev codebase to expert-curated standards**. The thesis: a hand-curated dev tree gives us a *sample-vs-sample* comparison against the snapshot. Disagreements between linter judgment and expert judgment (after the curation) are evidence of *missing signals* — slop patterns the rule set doesn't detect.

This is not ground truth — both samples reflect opinion — but it's a defensible bench for surfacing rule gaps.

### Methodological constraint

Structural decisions on the refactor are the user's. The agent executes mechanical work (renames, test updates, import sweeps) at the user's direction. Agent flags decision-shaped moments and pauses. This preserves the "expert-shaped" attribution of the curated dev tree.

## Open threads to resume after the pivot

These are documented so we don't lose them:

### From obs 09 (rule × cell matrix)

1. **Sprawl symbol-encoding gap** — all 41 sprawl findings on snapshot land in `---` or `-B-` because `Slop.symbol` is the alphabet member or `concept[NxN]` placeholder rather than a tokenizable identifier. Fix: have `lexical.sprawl` emit alphabet members as `metadata.alphabet`; have `violations_with_cells` consult it. Until fixed, sprawl can't be graded against the cross-tab.
2. **Imposters classifier consistency** — 16 of 22 imposters findings on snapshot land in `-BC` (hub) cell despite the profile classifier supposedly catching infrastructure cases. The cell-cross-tab is a strictly better filter than the profile classifier alone. Worth a follow-up: should imposters consult the cells, or should the cross-tab be the canonical filter?
3. **`(--C)` rule gap** — the diffuse-domain cell is populated in the lexicon (snapshot's `results, entry, check, identifier, parse, metrics, resolve`) but **zero existing rules fire on it**. None of the current rules knows how to say "this vocabulary should be a module." Candidate new rule: fires on `(--C)` tokens above a spread threshold. The pivot to expert curation should give us empirical examples to design this rule against.

### From obs 08 (second wave validation)

4. **Cell-aware corrective-action map** — the natural extension of `map_packets_to_actions` is to consult cell labels too. The sketch is in obs 08 and obs 09; needs implementation once we agree on the (rule, cell) → action table.

### From obs 06 (body-identifier sprawl)

5. **Layer-4 idiom filter for body identifiers** — `body_token_locations` is currently dominated by Python builtins (`list`, `len`, `int`) and stdlib idioms. Surfacing real body sprawl needs a per-language idiom filter. Deferred to backlog 09 per `docs/research/identifier-vocabulary.md`.

### From the IRIS contract (still active)

6. **Q9 / Q10 / Q8 — three planes resolution.** Q9 (frequency_head vs modal_tokens contract) and Q10 (packet_isolates parameterisation) are resolved and confirmed in the IR. Q8 (collapse-vs-keep-separate criterion) was resolved empirically by obs 07's matrix — keep separate. All recorded.
7. **D14 / D11 (second-wave methods)** — landed.
8. **D5 (packet_stability_over_git_history)** — deferred. Was originally a precondition for D3 (telemetry) which is invalid. Still useful for longitudinal observations; not load-bearing for current arc.

## The pivot's deliverable

The pivot's success looks like:

1. User-shaped dev tree, deemed clean enough by the user.
2. Re-run linter against the cleaned dev — expect a much smaller violation count than current dev's 559 violations (last full-suite count).
3. **The remaining violations + the slop the user can still see but the linter misses** = the dataset for designing new rules.
4. For each user-spotted slop pattern the linter missed: identify what citable signal (literature reference or empirical pattern) would detect it. Add to backlog as candidate rule.

## Pause-state checksums

- `git status` — has the snapshot rename + obs 09 + diagnostics.py additions uncommitted.
- Tests: 590 passed, 8 xfailed (as of last full run before the snapshot rename — subagent re-verified post-rename: same count).
- Active iris IR: revisions and overrides preserved on disk at `~/.claude/iris/-home-jgodau-work-personal-slop-src/`.
- Active mainline intent: `int_51778388` ("Eliminate legacy kernels…"), still drafting — the original goal is functionally complete; consider sealing before starting the refactor pivot's intent.
- Active `/goal` stop-hook: three-planes contract; conditions are met (first wave landed, obs 07 produced, second wave landed); auto-clears when read.

## Resuming the diagnostic arc later

When we come back, the natural next step is **case-by-case grading of the (rule × cell) matrix from obs 09** — we paused mid-case-01. The grading template is in that obs's "What to discuss next" section. Pick up there, or revise based on what we learn from the refactor pivot.
