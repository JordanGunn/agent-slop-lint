# Observation 05 — Diagnostic suite + threshold calibration + corrective actions

**Date:** 2026-05-17
**Primitives landed:** `slop.lexicon.diagnostics` (multi-scope violation counts, histogram bins, distribution summaries, `emit_diagnostic_report` JSON emit); `slop.lexicon.actions` (`map_packets_to_actions` packet-shape → refactor advisory). D8/D9/D10/D2 from the IRIS contract.
**Corpora:** v1.2.0 snapshot (78 files / 489 callables / 3 classes) and current dev (114 files / 749 callables / 25 classes).
**Filter:** `UNIVERSAL_NOISE` stripped throughout.
**Data:** `docs/research/observations/data/{05-snapshot-v1.2.0-diagnostic-with-actions.json, 05-dev-diagnostic-with-actions.json, 05-threshold-sweep.json}`.

## What's in the suite

Three composable surfaces let observation documents produce reproducible, queryable structured data:

- **Multi-scope violation counting** — run each lexical rule once on the corpus, then bucket findings by `{file, package, root, callable}`. Returns per-scope rule-fire counts that surface "which rule fires where".
- **Histograms + distribution summaries** — equal-width buckets for continuous data, power-of-2 buckets for skewed integer distributions (sprawl, packet sizes, frequency). Each summary carries n/mean/median/p90/max + histogram.
- **`emit_diagnostic_report`** — JSON-serialisable composite: `{corpus, distributions, packets, violations_by_scope}`. When a `class_vocabularies` map is supplied, packets are pre-split into pathological vs conventional and pathological packets carry their corrective-action advisory.

## Threshold calibration

Sweep across `(min_bags ∈ {3, 4, 5, 6, 8, 10}) × (min_association ∈ {0.5, 0.6, 0.7, 0.8, 0.9})`. Each cell shows `Np+Nc` (pathological + conventional packets after the class-ownership split). Full data in `05-threshold-sweep.json`.

### Snapshot

```
            assoc=0.5  0.6  0.7  0.8  0.9
callable scope
  bags=3       26+0   18+0  10+0   9+0   6+0
  bags=5       14+0    8+0   7+0   5+0   2+0
  bags=10       9+0    3+0   5+0   3+0   2+0

file scope
  bags=3       85+0   55+0  15+0   7+1   4+0
  bags=5       45+0   26+0  10+0   5+1   2+0
  bags=10      19+0   12+0   4+0   4+1   1+0
```

### Dev

```
            assoc=0.5  0.6  0.7  0.8   0.9
callable scope
  bags=3      31+13   19+10  13+9   7+6    5+4
  bags=5       14+10   10+7   9+7   4+5    2+3
  bags=10        9+8   6+5    6+5   1+4    0+2

file scope
  bags=3        81+9  55+16 16+26  9+19  3+16
  bags=5        40+2  34+4 13+23  8+17  2+14
  bags=10       22+0  22+4   9+21  5+15  1+11
```

### Reading the calibration

- **Snapshot has near-zero conventional packets at any threshold** (max 1 conv, at file/`bags=3, assoc=0.8`). Confirms what observation 04 already showed: the snapshot has essentially no class-based abstractions, so every packet is drift.
- **Dev's file-scope absorption ratio is a clean monotonic function of `min_association`**:
  - `assoc=0.5`: 5% conventional (filter barely fires)
  - `assoc=0.7`: 64% conventional
  - `assoc=0.9`: 87% conventional
- **Hub leakage at low association**: at `assoc=0.5`, 81 file packets in dev — many include hub tokens (`node`, `content`, `root`). At `assoc=0.7+`, hubs drop out.
- **Recommended default: `min_bags=5, min_association=0.7`**. Balances signal volume (10-13 pathological packets per corpus — small enough to grade by hand) against false-positive rate (hubs already filtered, conventional fingerprint absorbed in dev).
- **For aggressive review use `assoc=0.9`**: snapshot drops to 2 file-scope pathological packets, dev to 2. These are the highest-confidence drift signals.

## Distribution shapes

From `emit_diagnostic_report` on each corpus (thresholds: bags=5, assoc=0.7):

```
                         snapshot   dev
files                          78    114
callables                     489    749
distinct tokens               475    513
token_freq mean / max         6.0 / 144     5.3 / 149
token_file_spread max / p90    58 / 6        31 / 10
callable packets               7              16
file packets                  10              36
pathological / conventional
  callable                   7 / 0         9 / 7
  file                      10 / 0        13 / 23
```

**Notable shape changes from snapshot → dev:**

- Token *peak frequency* almost unchanged (144 → 149), but the *p90 file-spread* of tokens grew from 6 to 10. Vocabulary is more diffusely spread in dev than snapshot — possibly because the new ABC + per-grammar layout means each "category" token appears in many grammar files.
- File-scope packets grew dramatically (10 → 36), but two-thirds of dev's new packets are conventional. The architectural fingerprint of the `Language` ABC + concrete grammars dominates the raw count.
- Callable packet absorption ratio in dev: 7/16 = 44%. The class-ownership filter is doing real work even on callable-scope packets.

## Per-scope rule violation counts

Each row is a `(rule, scope-axis)` pair where the rule fired. Selected highlights (full data in JSON):

### Snapshot (root-scope, totals)

```
lexical.stutter      88
lexical.verbosity    59
lexical.sprawl       41
lexical.imposters    22
lexical.tautology    12
lexical.slackers     10
```

### Dev (root-scope, totals)

```
lexical.stutter      77   ↓
lexical.imposters    37   ↑↑
lexical.verbosity    25   ↓↓
lexical.sprawl       20   ↓↓
lexical.slackers     19   ↑
lexical.hammers       3   (was 0)
```

**Interpretation.** Slop's own refactors during this session collapsed `verbosity` and `sprawl` (consistent with the kernel-fold and FindOptions retirement), but `imposters` *grew*. That makes sense — the new `Lexicon` view methods take many small first-parameter clusters (`source`, `path`, `scope`, etc.), several of which fire as first-parameter clusters with mixed receiver-call profile. **The methodology surfaces drift the refactor introduced.**

## Corrective actions — first empirical grading

Each pathological packet maps to one of: `extract_dataclass`, `extract_module`, `missing_class`, `named_tuple`, `naming_convention`, `review`. Provenance shape (all_param / mostly_param / all_name / mostly_name / mixed) drives the classifier.

### Dev — callable-scope corrective actions

```
extract_dataclass        (1)
  [medium]  {exclude, include, parameters}   ← self-inflicted slop from this session!
named_tuple              (2)
  [low]     {config, slop}
  [low]     {since, until}
naming_convention        (6)
  [medium]  {add, parser, subparsers}        ← CLI subcommand convention
  [medium]  {config, run, slop}              ← rule-wrapper convention
  ...
```

The classifier correctly fingerprinted the `{exclude, include, parameters}` packet that this session itself created (added to many `Lexicon` distribution methods). It also caught the `add_parser(subparsers)` and `run_*(config) → Slop` conventions — both candidates for becoming named ABCs (Subcommand protocol; RuleContext dataclass).

### Snapshot — corrective actions

```
callable scope
  named_tuple (3):       {annotation, require}, {score, shared}, {kernel, languages}
  naming_convention (4): {excludes, globs, hidden, ignore, kernel, languages, no} ...

file scope
  extract_module (5):    {c, cpp, function, functions, ruby}, ...   ← language-handler dispatch family
  missing_class (2):     {excludes, globs, hidden, ignore, ...},    ← FindOptions
                         {config, rule, run, slop}                  ← rule-wrapper convention
  named_tuple (1):       {content, node}
  review (2):            {call, ruby}, {function, functions}
```

**The snapshot's FindOptions packet is classified as `naming_convention` at callable scope and `missing_class` at file scope** — not `extract_dataclass`. This is because the `kernel` token in the snapshot appears more often as an entity-name token (`find_kernel`, `imposters_kernel`, `hammers_kernel`, etc.) than as a parameter, breaking the all-param shape.

This is empirically correct for the snapshot: `kernel` in v1.2.0 *is* primarily an architectural marker on function names. The dev tree (which we wrote in this session) has no `*_kernel` functions left, so the equivalent retired packet wouldn't have surfaced.

**The classifier's first empirical grading is therefore methodologically correct** but exposes a refinement: the `mostly_param` shape (most tokens param-favoured, with one or two name-overlapping tokens) catches the cleaner refactor candidates while preserving the snapshot's nuance.

## What this satisfies in the contract

- **D8** multi-scope measurement: ✓ `count_violations_by_scope` operates on file/package/root/callable axes.
- **D9** histograms: ✓ `histogram_buckets` (equal-width) + `log_buckets` (power-of-2), plus `distribution_summary` for stat summaries.
- **D10** structured-data format: ✓ `emit_diagnostic_report` returns a JSON-serialisable composite. Two production runs landed at `docs/research/observations/data/`.
- **D2** corrective-action mapping: ✓ `map_packets_to_actions` with 6 categories, empirically graded on both corpora. The `{exclude, include, parameters}` self-detection is the highest-value finding.
- **D7** threshold calibration: ✓ this observation grades `(min_bags, min_association) × scope × corpus`; recommends `(5, 0.7)` as default, `(5, 0.9)` for aggressive review.
- **Conventional/pathological distinction**: ✓ baked into every layer; this observation explicitly separates the two on every reported packet.

## Open questions for next observations

1. **Provenance refinement.** The `mostly_param`/`mostly_name` thresholds are currently strict-majority. A weighted ratio (e.g. ≥ 75% of *occurrences* are parameters) might catch FindOptions-style packets where one token has heavy entity-name use. Worth grading.
2. **Multi-class coverage.** The class-ownership filter requires single-class subset coverage. Many dev file-scope pathological packets are absorbed by `cpp.Cpp` ∪ `base.Language` (the inheritance chain). Lifting the filter to "ancestor-chain union" would absorb more conventional fingerprints.
3. **Class-attribute vocabulary.** `Structure.class_vocabularies()` only includes method-name tokens. Dataclass field names would absorb more conventional packets — worth adding.
4. **Cross-rule packet correlation.** When the same scope (a file, a package) fires multiple lexical rules, the *combination* may itself be a signal. Worth a histogram of "how many distinct lexical rules fire on the same callable / file".

## What to build next

The contract's remaining deliverables:

- **D4** `body_identifier_token_source` — extends `callable_token_bags` / `file_token_bags` to optionally include body-identifier tokens. Lets packets catch sprawl across function bodies, not just signatures. Predicted to surface the `pdf` sprawled-across-functions case from observation 01.
- **D5** `packet_stability_over_git_history` — packet birth/death across commits via `slop.structure.git`. Originally a precondition for D3 (telemetry), which is invalid; still useful for the "did this packet retire across the refactor?" methodology obs 03 introduced.

D4 is small (parameter on existing methods); D5 is heavier (git-axis iteration + diffing). D4 next.
