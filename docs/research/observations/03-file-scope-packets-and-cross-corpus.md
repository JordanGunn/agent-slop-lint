# Observation 03 — File-scope packets + snapshot↔dev cross-corpus diff

**Date:** 2026-05-16
**Primitives landed:** `Lexicon.file_token_bags`; `scope='callable'|'file'` parameter on `cooccurrences` / `packets`; rename `min_callables → min_bags` for scope-agnostic counting.
**Corpora compared:** `docs/research/snapshots/v1.2.0/slop` (78 files) vs. `src/slop/` (112 files, current dev).
**Threshold:** `min_bags=5, min_association=0.7`, `UNIVERSAL_NOISE` stripped.

## The before/after experiment we wanted

```
                                callable scope    file scope
                                snap  dev  shared  snap  dev  shared
total packets                     7    16     2     10    36     1
```

### Confirmation: FindOptions is gone in dev

The 7-token `{excludes, globs, hidden, ignore, kernel, languages, no}` packet that dominated the snapshot is **absent in dev**. The kernel-fold retirement that happened in this session collapsed exactly the packet the methodology predicted. **First successful before/after experiment.**

Also retired from snapshot→dev:
- `{annotation, require}` — sentinel/escape-hatch parameter pair (presumably folded into something or renamed)
- `{score, shared}` — `min_score` / `min_shared` redundancy parameter pair
- `{c, cpp, function, ruby, ...}` — language-alphabet cluster

### Persistent across both corpora (stable conventions)

- `{run, slop}` at callable scope — the `run_X` returns `Slop` rule-wrapper convention
- `{since, until}` at callable scope — git log time-window parameters
- `{config, rule, run, slop}` at file scope — `slop/structure/rules/` and `slop/lexicon/rules/` consistently use this 4-token vocabulary

### New in dev (introduced this session)

- `{exclude, include, parameters}` at callable scope — **self-inflicted slop**. We added `exclude=` and `include_parameters=` keyword pairs across many `Lexicon` distribution methods. The pattern that fired on the snapshot is now firing on our own freshly-written code. The fix is real and small (move these into a single `TokenSourceConfig` or accept fewer keyword pairs).
- `{add, parser, subparsers}` — CLI subcommand `add_parser(subparsers)` convention, persistent because every command file uses it
- `{hidden, mutators, require}`, `{mutators, require}`, `{fn, mutators, require}` — `require_*` parameter family in the `hidden_mutators` rule
- `{escape, hatch}` — `escape_hatch_*` naming

## The bigger discovery: conventional packets vs. pathological packets

**File-scope packets in dev are enormous** — the largest contains *30 tokens* including members like:
`abstract, annotation, block, body, boolean, callable, case, classes, compensating, decision, decisions, else, escape, extract, hatch, import, literal, loop, nesting, nodes, numeric, op, operand, operator, operators, queries, switch, try, type, types`

These all co-occur because every file in `slop/language/grammars/*.py` (and every per-category enum in `slop/language/ast/*.py`) declares the **same total vocabulary** by interface requirement: every grammar implements `callable()`, `classes()`, `conditional()`, `loop()`, `operator()`, etc. The vocabulary is necessarily total.

**This is a fundamentally different signal than the FindOptions packet.** It is:

- **Conventional packet** — many tokens cluster across files because the *architecture requires every file to use every token*. The vocabulary is already owned by a defining class (`Language` ABC), and the file-level recurrence reflects that ownership, not undeclared structure.
- **Pathological packet** — many tokens cluster across files because *no one extracted the abstraction* and the tokens drift together by inertia. FindOptions is the textbook case.

**Both are detected by the same primitive today.** The cross-corpus diff exposed this immediately because the snapshot's per-grammar structure was less developed (fewer per-category enums); dev has the full ABC-with-many-required-methods layout, so the architectural fingerprint dominates.

### Candidate distinguishing signal: does a defining class already own this vocabulary?

If `Language.callable`, `Language.classes`, `Language.conditional`, etc. all exist as methods on a single class, then a file-scope packet of those names is conventional — the class is the abstraction the vocabulary expresses. If a packet's members are *not* methods/fields on any common class, it's a candidate pathological packet (missing abstraction).

This is a concrete, testable refinement. **Predicted next observation:** filter packets by "do the member tokens appear as method names or attribute names on a single class?" — keep only the ones that *don't*. The remaining packets should converge on the small actionable set.

## What this proves and what it changes

1. **The cross-corpus before/after methodology works.** The retirement of `find_kernel` produced exactly the packet retirement we expected. Slop's own refactors can be validated empirically against itself.
2. **Per-callable scope is the better-behaved primitive right now.** Hub/packet separation is clean. File scope needs an additional filter to be useful on architecturally regular codebases.
3. **The methodology already caught one fresh slop signal in dev** — the `{exclude, include, parameters}` keyword pair we replicated across the Lexicon distribution methods. This is the kind of catch we want to surface to an agent as a corrective recommendation.

## Open questions for next observation

1. **Class-ownership filter.** Can we cheaply detect "this packet's tokens are methods/attributes on class X" via the `Structure` view, and use that to filter conventional packets from pathological ones?
2. **Packet stability over time.** With one fixture and one dev tree we have one before/after. With git history, we could plot packet birth/death over commits. Useful for the telemetry layer eventually.
3. **The `{exclude, include, parameters}` finding suggests an immediate fix.** Worth grading: if we collapse `exclude=`/`include_parameters=` into a single `TokenSourceConfig` dataclass in `Lexicon` distribution methods, does the packet disappear?

## What to build next (suggested ordering)

1. **Class-ownership packet filter.** A pure-logic addition on top of existing primitives: given a packet and a `Structure` view, check whether its members appear as method names on any single class. Likely an order-of-magnitude reduction in conventional false positives.
2. **Once filtered packets are clean: define the first "corrective action" mapping.** Packet shape → suggested refactor. Output as advisory.
3. **Telemetry-layer prototype**: take a directory, emit `{packets, sprawl, sliced_metrics, corrective_actions}` as JSON to stdout. The first user is an agent reading its own work back.
