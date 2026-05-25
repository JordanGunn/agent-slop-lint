# Observation 09 — Rule × cell cross-tabulation

**Date:** 2026-05-17
**Primitive landed:** `slop.lexicon.diagnostics.violations_with_cells()` + `tabulate_rule_cell_matrix()` + `format_rule_cell_matrix()`. Joins Layer-1 rule violations with Layer-2 diagnostic cells.
**Corpus:** v1.2.0 snapshot.
**Thresholds (recorded inline):** `frequency_head(threshold=8)`, `spread_dominant(min_spread=5)`, `packets(min_bags=5, min_association=0.7)`, `UNIVERSAL_NOISE` stripped.
**Data:** `docs/research/observations/data/09-snapshot-rule-cell-matrix.json` (full 236 violation records with cell labels).

## What this observation does

For every lexical rule violation, look up the cited `symbol`'s tokens in the three planes (A=packets, B=frequency head, C=spread). Assign each violation a **primary cell** by priority (`ABC > AB-/A-C > A-- > -BC > -B- > --C > ---`). Tabulate as a `(rule × cell)` matrix.

The matrix is the empirical bridge between Layer 1 ("which rule fired?") and Layer 2 ("where in the lexicon does that finding sit?"). It's the foundation for cell-aware corrective-action mapping — the horizon goal of recommending "these belong in one module", "this is a missing class", "this is a missing interface", etc.

## The matrix

```
                     ABC    AB-    A-C    A--    -BC    -B-    --C    ---
─────────────────────────────────────────────────────────────────────────
lexical.stutter       22      .      .      .     43     12      .     11
lexical.verbosity      6      1      .      .     42      6      .      4
lexical.cowards        .      .      .      .      2      .      .      1
lexical.hammers        .      .      .      .      .      .      .      1
lexical.tautology      .      .      .      .      7      4      .      1
lexical.sprawl         .      .      .      .      .     11      .     30
lexical.imposters      .      .      .      .     16      2      .      4
lexical.slackers       .      .      .      .      7      1      .      2
lexical.confusion      .      .      .      .      .      .      .      .
```

Cell totals across all rules:

```
ABC   ████████████████████████████              28   (12%)  ← strong-signal
AB-   █                                          1
A-C                                              0
A--                                              0
-BC   ████████████████████████████████████████ 117   (50%)  ← HUB CELL
-B-   ████████████████████████████████████      36   (15%)  ← concentrated
--C                                              0
---   ████████████████████████████████████████  54   (23%)  ← long tail
```

## The headline finding

**Half of all snapshot violations (117/236, 50%) fire on tokens in the hub cell.** The rules are correct in the abstract — each detects a real pattern — but the majority of their citations are on infrastructure plumbing tokens that the diagnostics class as non-actionable. This is the empirical foundation for the proposition that *rule violations need cell-aware downgrading before being shown to a user*.

## Per-rule reading (with exemplars)

### Stutter (88 total)

- `ABC` (22): real semantic stutter, e.g.
  - `any_type_density_kernel` in `structural/any_type_density.py` (`kernel` is a packet member + frequent + spread)
  - `clone_density_kernel`, `npath_kernel`, etc. — the v1 architectural-marker stutter
- `-BC` (43): hub-driven stutter, e.g.
  - `cluster_patterns` in `lexical/sprawl.py` (`cluster`/`patterns` co-occur as parameters but don't bond to a specific other token)
  - `items_at_scope` (`scope` is plumbing)
- `-B-` (12): concentrated stutter — `GodModuleResult` in `god_module.py` (`module` is high-freq but local)
- `---` (11): tail — `match_dict`, `legacy_table` (tokens below threshold; arguably real stutter)

**Reading: ~50% of stutter is hub-driven, 25% is real semantic stutter.** A cell-aware advisory should downgrade `-BC` stutter findings.

### Verbosity (59 total)

- `ABC` (6): real over-naming of strong-signal concepts, e.g. `any_type_density_kernel`
- `-BC` (42): hub-driven verbosity — `migrate_legacy_rule_tables`, `_parse_numstat_log_output` (long names *because* of plumbing tokens)
- `-B-` (6): `_recursive_first_param_findings` (local concentrated)
- `AB-` (1): `_ruby_is_require_call` — the `require` token is in a tight local packet
- `---` (4): tail

**Reading: ~70% of verbosity is hub-driven.** Long names made up mostly of plumbing tokens are different in kind from long names made up of domain tokens — the former is a refactor signal (extract the plumbing-bearer), the latter a naming signal.

### Sprawl (41 total)

- `-B-` (11) + `---` (30): all sprawl findings land in non-packet cells. **No ABC cell.**

This is an instrumentation gap, not a methodological one: sprawl's `symbol` field is the alphabet member or `concept[NxN]` placeholder, so the cell-lookup doesn't find the real bonded vocabulary. The sprawl violations *are* real (we know FindOptions exists in the snapshot), but the matrix can't see them because the symbol encoding doesn't expose the packet members. **Action item:** sprawl should emit alphabet members as `metadata.alphabet` so the cross-tab can join on them.

### Imposters (22 total)

- `-BC` (16): hub-parameter clusters — `fn_node` (`fn`/`node` are plumbing), `pkg_files`, `file_paths`
- `-B-` (2): `raw`, `output` — local plumbing
- `---` (4): `cwd`, `result`

**Reading: 73% of imposters fire on hub-parameter clusters.** The existing imposters classifier *does* route some of these to `infrastructure` profile internally — but enough leak through as `missing_class`/`heterogeneous` profile to dominate the matrix. The cell-cross-tab is a stricter filter than the profile classifier alone.

### Tautology, slackers, cowards, hammers (16 total combined)

Tail rules, mostly `-BC` / `-B-` / `---`. Small sample sizes; no strong shape conclusions.

## What this enables for corrective-action mapping

The matrix is the empirical evidence behind a **cell-aware rule-output filter**. For each `(rule, cell)` combination we can now assign a translation:

| (rule, cell) | n  | what it means | corrective action |
|---|---:|---|---|
| `stutter ABC` | 22 | semantic stutter on bonded token | rename — the stutter is real |
| `stutter -BC` | 43 | hub-driven stutter | waive / downgrade — the stutter is structural plumbing |
| `verbosity ABC` | 6 | over-named bonded concept | extract a class/module around the bonded token; verbosity will drop |
| `verbosity -BC` | 42 | name dominated by plumbing tokens | extract a class for the *plumbing bearer* (FindOptions case) |
| `imposters -BC` | 16 | hub-parameter cluster | not a missing class — it's a shared parameter bearer; consider a context-object dataclass |
| `imposters ABC` | (none in snapshot) | bonded receiver cluster | **the classic "this should be a class" case** |
| `sprawl *` | 41 | (instrumentation gap — sprawl symbol doesn't tokenize) | needs the `alphabet` metadata fix first |

These are not yet *rules slop ships*. They're the agreed-upon translation table we now have empirical evidence to build. The next conversation is grading these translations against the actual snapshot: do any of them produce surprising results when traced back to source?

## The horizon: simple corrective actions

Per the goal contract's framing, we want rule output to eventually abstract up to:

- *"These belong in a single module"* — likely `(verbosity, -BC)` ∪ `(stutter, -BC)` ∪ `middle_spread` tokens that cluster spatially
- *"These should exist in their own package"* — likely `(--C)` middle-spread tokens that don't fit any existing package
- *"This class is actually two classes and an abstract class"* — likely `confusion` findings × `(ABC)` packet split (currently zero confusion fires on snapshot)
- *"Missing interface"* — likely `imposters ABC` cluster spanning multiple files (currently zero on snapshot)

The matrix gives us the substrate to write these mappings, but we are **not there yet**. Three blockers/gaps surface:

1. **Sprawl's symbol-encoding gap** (sprawl rule lands all 41 findings in `---` or `-B-`). Fix before the cross-tab can score sprawl meaningfully.
2. **Imposters classifier consistency**: 16 imposters findings fire on `-BC` cell despite the profile classifier supposedly catching infrastructure cases. The cell-cross-tab is a strictly better filter.
3. **No findings in `(--C)`** despite this being a populated cell in the lexicon (6 tokens on snapshot). **This is a gap to discuss: should a new rule fire on `(--C)` cell tokens?** None of the existing rules has a way to cite "vocabulary that should be a module."

## What this resolves and what it surfaces

- ✓ Validates the (rule × cell) framing — the matrix is sparse and structured, not noise.
- ✓ Empirically confirms the hub-cell dominance hypothesis: 50% of violations are infrastructure-driven.
- ✓ Confirms `stutter ABC` and `verbosity ABC` exist as small, high-confidence advisory categories.
- ✗ Surfaces sprawl's symbol-encoding gap as a blocker for cross-rule joining.
- ✗ Surfaces a possible new-rule opportunity for `(--C)` cell tokens.

## What to discuss next

The horizon framing needs three things, in order:

1. **Grade the matrix together.** Walk through each cell-rule combination, decide whether the corrective-action translation in the table above is the right one. Override where the data disagrees with intuition.
2. **Decide on sprawl-symbol fix.** Either patch the rule to expose alphabet members in `symbol`/`metadata`, or change the cell-lookup to consult `metadata.alphabet` when present.
3. **Decide on the `(--C)` rule gap.** Is the absence of any rule firing on diffuse-domain tokens a feature (we don't have an answer for "what to do with cross-cutting vocabulary") or a gap (we should design a rule that fires here)?

The substrate is now ready for that discussion.
