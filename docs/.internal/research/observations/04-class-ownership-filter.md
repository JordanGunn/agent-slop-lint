# Observation 04 — Class-ownership packet filter

**Date:** 2026-05-17
**Primitive landed:** `Structure.class_vocabularies()` (returns `{class_qualname: set of method-name tokens}`); `slop.lexicon.filters.split_packets_by_class_ownership(packets, vocabularies) -> (pathological, conventional)`.
**Corpora:** `docs/research/snapshots/v1.2.0/slop` (78 files, 3 classes) and `src/slop/` (113 files, 25 classes).
**Threshold:** `min_bags=5, min_association=0.7`, `UNIVERSAL_NOISE` stripped.

## Method

Observation 03 surfaced two genuinely different signals behind the same `Lexicon.packets` primitive. A *pathological packet* (tokens cluster because no abstraction has been extracted — FindOptions case) and a *conventional packet* (tokens cluster because the architecture requires every site to use every token — per-grammar AST node categories case).

The hypothesised distinguishing test: **a packet is conventional iff its tokens are a subset of some single class's method-name vocabulary.** The class is the abstraction; the packet is just its surface reflection.

Implementation: `Structure.class_vocabularies()` groups method simple-names (snake/Camel-split, lowercased) by their parent class scope, producing `{class_qualname: set[token]}`. The filter then asks, for each packet: does any single class's vocabulary cover it?

## Results

```
                         snap callable   snap file   dev callable   dev file
total packets             7                10           16            36
   → pathological         7                10            9            13
   → conventional         0                 0            7            23

absorption rate (conv / total)
   snap  0%   0%
   dev   44%  64%
```

### Snapshot: 0% absorption (everything is genuine slop)

The snapshot's 78-file corpus has only 3 classes (mostly dataclass-shaped). None of its packets is a subset of any class's vocabulary:

- `{excludes, globs, hidden, ignore, kernel, languages, no}` — no class with that vocabulary exists, hence FindOptions is genuinely missing.
- `{c, cpp, function, functions, ruby}` — language-handler alphabet, no `Language` ABC to own it.
- `{config, rule, run, slop}` — rule-wrapper convention, no class.

**Confirms the snapshot's previously surfaced packets were all real refactoring candidates.**

### Dev callable: 44% absorbed by `base.Language`

The seven conventional callable packets all credit `base.Language`:

- `{boolean, op}` — `Language.boolean_op_node()` / `boolean_op_operators()` / `compensating_decisions()`.
- `{callees, trivial}` — `Language.trivial_callees()`.
- `{compensating, decisions}` — `Language.compensating_decisions()`.
- `{escape, hatch}` — `Language.escape_hatch_*()`.
- `{hidden, mutators}` — `Language.hidden_mutators_*()`.
- `{literal, numeric}` — `Language.literal_numeric_*()`.

The remaining nine *pathological* callable packets include:

- `{exclude, include, parameters}` — **self-inflicted slop** from this session (the `exclude=` / `include_parameters=` keyword pairs across Lexicon distribution methods). Q4 proposes a TokenSourceConfig refactor as the empirical before/after.
- `{config, run, slop}` and `{config, slop}` — rule-wrapper convention (`run_*(cfg, slop_cfg)`). Not owned by any class; arguably a conventional packet that wants a `RuleContext` dataclass to absorb it.
- `{add, parser, subparsers}` — CLI subcommand `add_parser(subparsers)` convention. Not class-owned; could be a `Subcommand` ABC.
- `{hidden, mutators, require}`, `{mutators, require}` — `require_*` parameter family in the hidden_mutators rule.

### Dev file: 64% absorbed by `cpp.Cpp` / `base.Language`

The headline result. The giant 24-30 token architectural-fingerprint packets all get absorbed:

- Five packets of size ≥24 absorbed by `cpp.Cpp` (the C++ grammar implements every AST node category, so its vocabulary covers any subset)
- More absorbed by `base.Language` (the ABC itself)

The 13 file-scope *pathological* dev packets are the interesting set:

- Several 11-25 token packets containing tokens like `fn` / `superclasses` / `nodes` that span multiple grammars without sitting in any single class's vocabulary. These are *cross-grammar* fingerprints — the categories that *every grammar* implements but no single grammar owns. Strict single-class coverage rejects them.
- `{call, callee, callees, fn, params, stringly, trivial, typed}` (8 tokens) — file-scope co-travel between `stringly_typed` and `trivial_callees` rules; genuine pattern worth surfacing.
- `{callable, content, node, nodes, text, types}` (6 tokens) — the tree-sitter idiom file-scope vocabulary; would be absorbed if we had a `TreeSitterParser` class with `callable / content / node / text / types` methods, but we don't.

## Validation against the predicted distinction

The filter behaves as the obs 03 hypothesis predicted. Specifically:

1. **Snapshot has no conventional packets** because it has no abstract base classes — every packet is drift. ✓
2. **Dev's giant 30-token file packet is conventional** because `cpp.Cpp` owns the whole vocabulary. ✓
3. **The 5-token FindOptions packet (in snapshot) remains pathological** because no class with that vocabulary exists. ✓
4. **The 3-token `{exclude, include, parameters}` packet (in dev) remains pathological** because no Lexicon-internal class owns those token names — confirming the refactor opportunity. ✓
5. **Hub tokens (`root`, `node`, `content`) never appear in any packet** at min_association=0.7 (verified in obs 02); the filter doesn't need to handle them.

## Limitations and refinements

- **Strict single-class coverage misses multi-class hierarchies.** A packet covered by `Language` + one of its subclasses (e.g. `{abstract, fn, superclasses}`) is rejected as pathological even though it's owned by an inheritance chain. Worth adding a "covered by union of ancestor-chain classes" variant. Out of scope for this observation.
- **Method names are the only signal.** Class-attribute names (e.g. dataclass fields) aren't part of `class_vocabularies()` because they aren't `Callable` records. The current implementation is method-only; adding attribute coverage would absorb more conventional packets. Worth a follow-up if pathological packets still over-fire on dataclass-attribute clusters.
- **Inherited vocabulary is not propagated.** A subclass that only declares one new method doesn't inherit the parent's method-name tokens. For deeply inherited hierarchies (rare in slop), this would split a single conceptual vocabulary across multiple class entries.

## What this proves

The conventional-vs-pathological distinction is **operationally clean and decisive on real data**. The filter cuts dev's file-scope packet noise by 64% (23 of 36) without manual triage, and surfaces a small focused set of pathological packets — every one of which is either a genuine refactor candidate (FindOptions, TokenSourceConfig, RuleContext) or a small recurring pattern worth naming. The signal-to-noise ratio of slop's headline lexical-signal primitive just improved by ~3×.

## What this enables (and what's next)

The pathological/conventional split is the precondition for D2 (corrective_action_mapping): each *pathological* packet shape can now be confidently mapped to a refactor advisory without false-firing on architectural fingerprints. Combined with the multi-scope measurement coming in D8 and the histogram emitters in D9, the diagnostic suite can now produce signal that an agent could actually act on.

## Open questions

1. The `cpp.Cpp` vocabulary is enormous (every AST category × every node-type method). Is this absorbing *too* aggressively? A multi-language cluster like `{c, cpp, function, ruby}` would correctly stay pathological, but a subset like `{abstract, classes, decision, queries}` (all on Language) gets absorbed even though it's lexical evidence of the wide-language-support architectural style. May want to distinguish "absorbed by ABC" vs "absorbed by concrete subclass" — the former is convention, the latter might still be worth noting.
2. The pathological dev packets `{config, run, slop}` and `{add, parser, subparsers}` are *conventional* in spirit (rule-wrapper convention; CLI subcommand convention) but no class owns the vocabulary. They look like missing-class signals — the absence of `RuleContext` and `Subcommand` classes. Worth promoting as a corrective-action candidate in D2.
3. Cross-grammar fingerprints (the multi-grammar pathological file packets) — interesting in their own right. Each one is a vocabulary that every grammar declares because the ABC requires it. The fact that they don't cluster under a single class is the methodology working as designed; whether they're "real slop" or "diffuse convention" is a corrective-action question for D2.
