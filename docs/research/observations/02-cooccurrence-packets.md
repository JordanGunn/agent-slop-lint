# Observation 02 — Co-occurrence packets

**Date:** 2026-05-16
**Corpus:** `docs/research/snapshots/v1.2.0/slop`
**Primitive landed:** `Lexicon.callable_token_bags`, `Lexicon.cooccurrences`, `Lexicon.packets`.
**Filter:** `UNIVERSAL_NOISE` stripped throughout.

## Method

For each callable, build a token bag from its name + parameter names (snake/Camel-split, lowercased). Two tokens *co-occur* once for every bag they both appear in. A *packet* is a token set where every pair has association

```
assoc(a, b) = cooccurrences(a, b) / max(freq(a), freq(b)) >= threshold
```

and each token appears in ≥ N callables. **Max-normalised association** is the key choice — it distinguishes mutual packets (tokens that always travel together) from universal hubs (`root`, `node`, `content` — frequent but associated with nothing in particular).

## Results — strong packets (min_association=0.9, min_callables=5)

```
#1  (5 tokens)  excludes · globs · hidden · ignore · no
#2  (2 tokens)  annotation · require
```

**Packet #1 is the predicted `FindOptions` cluster.** Five parameters of `find_kernel`, propagated across every consumer. `no` is from `no_ignore` (tokenises into `no` + `ignore` separately). `languages` falls out at threshold 0.9 because a few callers take excludes/hidden/ignore/globs without languages — at threshold 0.7 it joins.

**Packet #2** is `require_annotation` — a parameter pair recurring across multiple sentinel/escape-hatch rules.

## Loose packets (min_association=0.7, min_callables=5)

```
#1  (7 tokens)  excludes · globs · hidden · ignore · kernel · languages · no
#2  (6 tokens)  excludes · globs · hidden · ignore · kernel · no
#3  (2 tokens)  annotation · require
#4  (2 tokens)  kernel · languages
#5  (2 tokens)  run · slop
#6  (2 tokens)  score · shared
#7  (2 tokens)  since · until
```

Every loose packet is a real structural pattern:

- `{excludes, globs, hidden, ignore, languages, no, kernel}` — the full FindOptions cluster + the `kernel` token (which co-travels because every callable named `*_kernel` takes these parameters).
- `{annotation, require}` — `require_annotation` parameter packet (sentinels / escape_hatches).
- `{run, slop}` — the rule-wrapper convention: `run_X` functions return `Slop` findings. Lexical evidence of the rule-registry pattern.
- `{score, shared}` — `min_score` / `min_shared`, both threshold parameters in `structural.redundancy`. A pair too small to refactor away but coherent as a named tuple.
- `{since, until}` — git log time-window parameter pair.

## Key validation: hubs do NOT cluster

`root` (58 callables), `node` (144 occurrences), `content` (94), `config` (110), `path` (36) — none of these appear in any packet. The math behaves: they have high frequency but their max-normalised association with any specific other token is low (they appear in many callables that *don't* share the same other tokens). Confirms the design rationale of using `max(freq)` instead of `min(freq)` for the normalisation.

## What this proves

**Co-occurrence + max-normalised association cleanly separates the actionable from the structural noise.** The same `lexical.sprawl` finding ("excludes appears in 30 files") that flagged both packet members AND infrastructure hubs in Observation 01 is now sharpened: packets are clustered, hubs are not. A rule that *only* fires on packet membership ≥ 3 tokens would have produced one actionable finding here (FindOptions) instead of a 15-token mixed signal.

## Corrective-action mapping (first cut)

Each packet category implies a different corrective action:

| Packet shape | Corrective action |
|---|---|
| ≥ 3 tokens, all parameter-names, sharing call sites | **Extract a dataclass** (FindOptions case) |
| 2 tokens, parameter-pair, recurring across many callables | **Named tuple or kwargs-only signature with documentation** |
| Tokens spanning name+param consistently | **Naming convention pattern** (run-X-returns-Slop case) — surfaces the implicit registry idiom |
| ≥ 3 tokens, all in entity names (no params) | **Extract a module** by the shared concept |

These mappings are speculative until we grade them on more corpora. But the categories are reasonable and each implies a different output advisory.

## Open questions for the next observation

1. **Cross-corpus.** How do the packets in the current `src/slop/` dev tree compare? Did the `find_kernel` retirement actually eliminate the FindOptions packet, or did it just relocate?
2. **Body-identifier inclusion.** Packets currently use name + parameter tokens. Adding body identifiers would catch the `pdf` use case (a token sprawled across function *bodies*, not signatures). Worth a separate observation comparing the two token sources.
3. **Module-extraction packets.** All our current packets are parameter packets. The thesis predicts module-extraction packets exist too — names that travel together across files but not parameters. Need a different aggregation: per-file token bags instead of per-callable.
4. **Calibration.** What thresholds (min_callables, min_association) maximally separate packets from noise across many corpora? Currently 0.9 / 5 is a guess from one fixture.

## What we need to build next (suggested ordering)

1. **Per-file token bags + file-level packets** — extend `callable_token_bags` to a sibling `file_token_bags`, then run `packets` on those. Surfaces the module-extraction pattern (vs. the dataclass-extraction pattern we have now).
2. **Cross-corpus comparison helper** — load two roots, diff their packet sets. First real before/after experiment: snapshot vs. dev.
3. **`slop research dump`** subcommand serialising `{modal, sprawl_candidates, packets, per_package_alphabets, package_overlap_matrix}` for a given root, as JSON. Feeds Jupyter for distribution plots.
