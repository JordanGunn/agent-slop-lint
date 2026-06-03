# Observation 07 — Three planes of evaluation: overlap matrix

**Date:** 2026-05-17
**Primitives landed:** `Lexicon.hapax_ratio`, `Lexicon.frequency_head(threshold=...)`, `Lexicon.spread_dominant(min_spread=...)`. First wave per A12 (R6 mitigation).
**Corpora:** v1.2.0 snapshot (78 files / 489 callables / 475 distinct tokens) and current dev (114 files / 749 callables / 513 distinct tokens).
**Thresholds:** `frequency_head(threshold=8)` (~corpus p90), `spread_dominant(min_spread=5)`, `packets(min_bags=5, min_association=0.7)`. `UNIVERSAL_NOISE` stripped throughout.

## Method

Three planes, each kept distinct with its own threshold and return type:

- **Plane A — Association density** — token is a member of some packet (`Lexicon.packets`)
- **Plane B — Distribution position** — token's frequency ≥ data-derived head threshold (`Lexicon.frequency_head`)
- **Plane C — Spread** — token's file-spread ≥ threshold (`Lexicon.spread_dominant`)

For each token in the union of any-plane membership, classify into one of the 8 cells of the 2×2×2 cube: `(in_A?, in_B?, in_C?)`. The cell occupancy distribution is the empirical answer to "do the planes converge or diverge?"

Hapax ratio (Lexicon-wide singleton fraction) records the long-tail noise floor as a single scalar.

## Results

### Hapax ratios

```
snapshot: 0.373   (177/475 tokens appear exactly once)
dev:      0.392   (similar shape — Zipf tail is consistent)
```

Both corpora carry roughly 37-39% one-off vocabulary. Stable across the refactor — the long tail is a structural property of identifier corpora (Pierret & Poshyvanyk 2009; Newman 2017), not an artifact of any particular implementation.

### Overlap matrix — snapshot

```
Plane A (packet members):    15 tokens
Plane B (frequency head):    81 tokens
Plane C (spread dominant):   63 tokens
Universe (any plane):        91 tokens

Cell                                            n   exemplars
(ABC)  all three planes                         9   excludes, globs, hidden, ignore,
                                                    kernel, languages, no, run, slop
(-BC)  freq + spread, no packet                48   body, build, c, call, check,
                                                    cluster, collect, compute, +40 more
(-B-)  freq only                               22   category, classes, cmd, extractor,
                                                    filter, go, imports, julia, +14 more
(--C)  spread only                              6   block, count, depth, e, method, relative
(A--)  packet only (small/local)                4   score, shared, since, until
(AB-)  packet + freq, no spread                 2   annotation, require
(A-C)  packet + spread, no freq                 0   (empty)
(---)  none                                     0   (by construction)
```

### Overlap matrix — dev

```
Plane A:    28 tokens
Plane B:    84 tokens
Plane C:    91 tokens
Universe:  106 tokens

Cell                                            n   exemplars
(ABC)  all three planes                        17   add, boolean, compensating, config,
                                                    decisions, escape, hatch, hidden, +9 more
(-BC)  freq + spread, no packet                55   abstract, annotation, args, block,
                                                    body, build, c, call, +47 more
(-B-)  freq only                                8   category, filter, log, output, raw,
                                                    rules, token, violations
(--C)  spread only                             15   callables, callee, classify, collect,
                                                    count, definition, functions, +8 more
(A--)  packet only                              3   npath, since, until
(AB-)  packet + freq, no spread                 4   exclude, include, parameters, vocab
(A-C)  packet + spread, no freq                 4   callees, stringly, trivial, typed
```

## What the matrix proves

The three planes **do not collapse**. Every cell except `(---)` (empty by construction) is occupied in dev, and 6 of 7 non-empty cells are occupied in snapshot. Token membership is genuinely cell-dependent: a token's coordinates in the cube carry information that no single plane reproduces.

The decision criterion from Q8 ("collapse-vs-keep-separate") is resolved empirically here: **keep separate**. The planes measure orthogonal aspects of vocabulary structure. Collapsing to a single "hub-or-not" boolean would erase signal that's visible in the cell breakdown.

## What each cell corresponds to, empirically

- **`(ABC)` — the unambiguous advisory zone.** Tokens that are *frequent*, *spread*, AND *bonded* in a packet. In snapshot this is exactly the FindOptions packet + the `run/slop` convention. In dev it's 17 tokens covering the surviving conventions (CLI, hidden_mutators, escape_hatches). These are the highest-confidence corrective-action candidates.
- **`(-BC)` — the hub signature.** High freq + high spread + NOT in any packet. Largest cell in both corpora (48 / 55). This is exactly the "spread without bonding" pattern we hypothesised was the hub diagnostic. Words like `body`, `node`, `content`, `c`, `call`, `build` — universally used, never specifically bonded. *This cell is the empirical definition of a hub.*
- **`(-B-)` — concentrated-vocabulary zone.** High freq, low spread. Local intensity: token appears many times within a small file set. Snapshot's `julia, go, imports, extractor` etc. live here — per-language handlers in `structural/`. Dev's `rules, output, violations` — concentrated in specific modules.
- **`(--C)` — diffuse-domain zone.** Moderate freq + high spread. Cross-cutting vocabulary that doesn't crest the head. Often the *most interesting* refactor candidates because they're spread enough to matter but not high-volume enough to be hubs. Dev's `callables, classify, definition, functions` look like they implicate a missing common-traversal abstraction.
- **`(AB-)` — packet + freq + local.** A frequent packet living in a small scope. Dev's `{exclude, include, parameters, vocab}` is here — *our self-inflicted slop*, surfaced again. Tight cluster, repeated often, but confined to the Lexicon view's distribution methods.
- **`(A-C)` — packet + spread + low freq** (dev only). Tight cross-file packets that don't have high raw frequency. `{callees, stringly, trivial, typed}` — small but cross-cutting. Worth surfacing.
- **`(A--)` — small local packets.** `{since, until}`, `{score, shared}`. Pair-shaped tight clusters in narrow scope.

## Decision on second wave

Per A12, the second-wave methods (`middle_spread`, `packet_isolates`) land only if obs 07 shows them non-redundant. The matrix is unambiguous:

- **`middle_spread` is non-redundant.** It names cells `(--C)` and `(-BC)` minus the head — the diffuse-domain and hub-candidate zones. Currently callers must manually subtract the head from the spread-dominant list. A named primitive removes the subtraction step.
- **`packet_isolates` is non-redundant.** It names cell `(-BC)` directly — high-frequency tokens that fail to form packets. The empirical hub diagnostic. Currently callers must combine `frequency_head` with packet-set-subtraction; a named primitive makes the hub identification one call.

**Both second-wave methods should land**, with the docstring on each citing this observation as the empirical motivation.

## Cross-corpus reading

Comparing snapshot vs. dev cell occupancy:

```
Cell    snapshot  dev   Δ
(ABC)        9    17   +8     dev has more strong signals — but they're
                              mostly conventional packets per obs 04
(-BC)       48    55   +7     hub population grew slightly (more files)
(-B-)       22     8  -14     concentrated vocab collapsed (per-language
                              kernels were absorbed by Language ABC)
(--C)        6    15   +9     diffuse-domain grew — the new substrate
                              surfaces more cross-cutting concepts
(A--)        4     3   -1     stable
(AB-)        2     4   +2     including our self-inflicted packet
(A-C)        0     4   +4     new cross-file packets in dev's substrate
```

Interpretation: the kernel-fold + substrate refactor moved tokens from `(-B-)` (concentrated) toward `(--C)` (diffuse) and `(ABC)` (strong-signal). This is consistent with the architecture: per-language handlers (which created concentrated vocabulary in `structural/`) became method dispatchers on the `Language` ABC (which creates diffuse vocabulary because every grammar uses every category).

## What this resolves

- **Q8 (collapse decision rule)** — Resolved empirically: keep the planes separate; the cell-occupancy distribution is informative.
- **R6 (surface bloat risk)** — Resolved: the matrix shows `middle_spread` and `packet_isolates` are non-redundant. Second wave is justified.
- **A9 (planes kept distinct)** — Validated by data.
- **First-wave methods** (`hapax_ratio`, `frequency_head`, `spread_dominant`) — landed, tested, exercised against both corpora.

## What this enables

The 8-cell breakdown is the empirical basis for a *cell-aware corrective action map*. Today's `slop.lexicon.actions.map_packets_to_actions` only considers packet shape; it could be sharpened to consider cell membership:

- `(ABC)` packets → high-confidence dataclass / class-extraction advisories
- `(AB-)` packets → "local convention worth documenting" (smaller refactor)
- `(A-C)` packets → "cross-cutting bundle, possibly utility-extraction"
- `(A--)` packets → "small local pair, low priority"

That's a follow-up observation. Recording the structure now so it's available when the corrective-action map is upgraded.

## Open questions for the next observation

1. **The `(--C)` zone in dev contains `callables, classify, definition, functions, identifier`** — looks like a missing common-traversal abstraction. Worth manual grading: is there an `Inspector` / `Visitor` class waiting to emerge?
2. **The `(AB-)` cell is small but precise** — should the corrective-action map weight it differently from `(ABC)`? Probably yes (smaller scope → smaller refactor).
3. **Snapshot has 9 strong-signal `(ABC)` tokens covering 1 FindOptions packet + 1 run/slop convention. Dev has 17 `(ABC)` tokens covering ~5-7 packets.** Does this mean dev has *more* slop, or more well-bonded conventions? Worth comparing against the corrective-action labels assigned in obs 05.
