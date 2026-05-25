# Observation 06 — Body-identifier sprawl + Layer-4 filter need

**Date:** 2026-05-17
**Primitive landed:** `Lexicon.body_token_locations()` — walks each callable's body AST and emits a `{token: set[path]}` map for every leaf identifier reference inside (snake/Camel-split, lowercased; single-underscore-prefixed names skipped per Python privacy convention, dunders kept). D4 from the IRIS contract.
**Corpora:** v1.2.0 snapshot and current dev (same as obs 04/05).
**Filter:** `UNIVERSAL_NOISE` stripped throughout. **Spoiler: this turned out not to be enough.**

## Top body-only tokens (token appears in bodies but not in any signature)

### Snapshot (top 10, all in ≥27 files)

```
list (65)   len (59)   analyzed (42)   int (35)   sorted (31)
extend (30) metadata (28)   message (28)   exclude (27)   error (27)
```

### Dev (top 10)

```
list (61)   len (46)   int (37)   tuple (37)   errors (36)
error (28)  end (27)   frozenset (26)   strip (24)   child (23)
```

## What this exposes

The primitive works correctly — it surfaces tokens spread across callable bodies that the existing `token_locations()` would miss. But **the dominant signal is Python language idioms, not missing modules**:

- `list`, `len`, `int`, `tuple`, `sorted`, `frozenset` — builtin constructors / functions
- `extend`, `strip`, `append`, `split`, `items` — stdlib container methods
- `error`, `errors`, `message`, `child`, `end`, `metadata` — common variable names that recur across error handling, AST walking, parser plumbing

None of these implicate a missing module. They're the lexical fingerprint of "this is Python code that does normal Python things." Whereas the obs 01 `pdf`-sprawl prediction *would* have surfaced cleanly here if the snapshot had `pdf` references in bodies — the primitive is right, but the noise is wrong.

## The Layer 4 filter problem

`UNIVERSAL_NOISE` strips Newman 14 + English glue (`a`, `length`, `id`, `pos`, …, `the`, `is`, `to`, …). It does **not** strip per-language ecosystem idioms — Python builtins, common stdlib container methods, exception-handling vocabulary. The docs already note this as deferred:

> Layer 4 (per-language ecosystem idioms) are deferred to docs/backlog/09.md.

The body-identifier walk surfaces this gap because body identifiers are dominated by Python idioms, whereas signature tokens (the `token_locations()` source) are dominated by domain vocabulary. **D4 didn't just land a primitive — it landed empirical evidence that the deferred Layer 4 filter is now load-bearing for body-sprawl analysis.**

## Sketch of a Layer 4 filter

A minimal Python-only filter would strip:

```
Builtins:        list dict tuple set frozenset int float str bool bytes type
                 len range sorted reversed enumerate zip map filter any all
                 min max sum abs round print isinstance issubclass hasattr
                 getattr setattr delattr callable iter next vars locals globals
Common methods:  append extend insert remove pop clear update get items keys
                 values copy join split strip startswith endswith lower upper
                 format replace count index find encode decode read write
Exception/control: error errors message exception raise return yield
```

Roughly 60-80 tokens. Each would be ineligible for body-sprawl signal but kept in entity-name analysis (a class named `Error` is meaningful; a variable named `error` mostly isn't).

For the current observation arc this is **out of scope** — building a calibrated Python-idiom filter against multiple corpora is a separate observation. Noted for the backlog.

## What this means for the corrective-action layer

The `body_token_locations()` primitive should NOT be wired into `emit_diagnostic_report` until the Layer 4 filter exists. Without it, the report would surface "missing module: `list`" advisories that are pure noise.

Keeping the primitive available, unwired, lets future observations exercise it manually until calibration improves.

## What this satisfies in the contract

- **D4** `body_identifier_token_source`: ✓ landed as `Lexicon.body_token_locations()`. Tested. Empirically exercised against both corpora. The primitive is correct; the calibration question (Layer 4 filter) is surfaced for future work rather than baked in prematurely.

## Open questions for next observations

1. **Layer 4 filter calibration.** Build a Python-idiom block list, grade it against snapshot + dev. The right list should leave the dev `pdf`-equivalent (something like `cluster`, `packet`, `affix` — domain tokens that recur in bodies) intact while removing `list` / `len` / `int`.
2. **Cross-source merge.** Should sprawl analysis combine `token_locations()` + `body_token_locations()` as one map, or keep them separate? Combined gives the "every place this token appears" view; separate lets the corrective-action mapping distinguish "shows up in N signatures" (extract dataclass) from "shows up in N bodies" (extract module / utility).
3. **Body-identifier packets.** Currently `cooccurrences()` / `packets()` operate on signature tokens only. Body-identifier packets could surface "tokens always referenced together inside the same function" patterns. Worth grading once Layer 4 is in place.

## What we built across observations 01-06

```
01  baseline-snapshot                  freq, modal, alphabet, by_file, by_package, token_locations
02  cooccurrence-packets               callable_token_bags, cooccurrences, packets
03  file-scope-packets + cross-corpus  file_token_bags; conventional vs pathological discovery
04  class-ownership-filter             Structure.class_vocabularies, split_packets_by_class_ownership
05  diagnostic-suite + thresholds      multi-scope violations, histograms, JSON emit,
                                       corrective_action_mapping, threshold calibration
06  body-identifier-sprawl             body_token_locations + Layer 4 gap
```

Six observations, each producing reproducible numbers, conventional/pathological separation where applicable, and explicit threshold records. JSON snapshots at `docs/research/observations/data/` for re-analysis.

D5 (`packet_stability_over_git_history`) remains untouched. It was originally listed as a precondition for D3 (telemetry, now invalid). Without the telemetry consumer, D5's value is "did this packet retire across the slop refactor?" — which observation 03 already demonstrated as a one-shot diff. Per A4 (internal research; no shipped telemetry yet), promoting D5 from "useful prototype" to "must-build" is deferrable until either (a) D3 is re-scoped or (b) a longitudinal observation specifically needs commit-by-commit stability data. Recording as a remaining open deliverable rather than satisfied.
