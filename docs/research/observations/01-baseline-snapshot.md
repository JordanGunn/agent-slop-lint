# Observation 01 — Baseline snapshot

**Date:** 2026-05-16
**Corpus:** `docs/research/snapshots/v1.2.0/slop` (86 Python files, ~199 callables)
**View methods:** `Lexicon.frequencies`, `modal_tokens`, `alphabet`, `coverage`, `overlap`, `token_locations`, `by_file`, `by_package` (landed in this session).
**Filter:** `UNIVERSAL_NOISE` (Newman 14 + English glue) stripped throughout.

## What we ran

Per-scope distribution dump against the v1.2.0 snapshot — first exercise of the new `Lexicon` view methods. No co-occurrence primitive yet; sprawl-by-file-count only.

## Top 15 tokens snapshot-wide

```
 144  node           110  config          110  root
  94  content         73  name             61  rule
  53  file            39  run              37  language
  36  function        36  path             34  no
  34  slop            34  excludes         32  globs
```

**Interpretation.** Two distinct populations are visible by inspection alone:

- *Domain vocabulary* — `rule`, `slop`, `language`, `function`. These name the things the codebase is *about*.
- *Infrastructure vocabulary* — `node`, `content`, `root`, `path`, `file`, `config`. These name values *threaded through* the codebase but not its subject.

The dominant tokens are infrastructure, which is itself a signal: the codebase spends more naming budget plumbing values around than expressing its domain.

## Sprawl candidates (token in ≥3 files, no module by that name)

```
N= 58  root        N= 31  rule           N= 31  run
N= 30  kernel      N= 30  excludes       N= 29  hidden
N= 29  ignore      N= 28  globs          N= 27  name
N= 27  slop        N= 23  languages      N= 18  content
N= 17  node        N= 17  max            N= 16  hint
```

## The headline finding: a missing dataclass

Five tokens travel together in essentially every file:

```
excludes (30)  hidden (29)  ignore (29)  globs (28)  languages (23)
```

These are the parameter list of `find_kernel`. They appear *as a packet* — every call site takes all five, threaded through every wrapper. They are an undeclared `FindOptions` dataclass spread across 30 files. A single refactor (introduce the dataclass, pass it as one parameter) collapses all five sprawl readings at once.

**This is the thesis in microcosm:** the lexical signal points at a structural component the codebase has not declared.

## Per-package vocabulary signatures

```
.          : node(144), config(110), root(110)
_ast       : query(7),  language(6), path(4)
_compose   : file(8),   root(8),     log(7)
_fs        : find(3),   fd(3),       type(3)
_lexical   : name(17),  cluster(13), min(13)
_structural: node(131), content(81), root(43)
_text      : pattern(4), grep(3),    rg(2)
_util      : check(3),  tool(3),     name(3)
rules      : config(69), run(34),    root(34)
```

Each package has a coherent dominant vocabulary that matches its purpose. `_structural` is overwhelmingly tree-sitter walking (node, content, root). `rules` is config-plumbing (config, run). `_lexical` is clustering (cluster, min). The signatures are sharp enough that a vocabulary fingerprint could plausibly classify which package a function belongs to.

## What this tells us

The simplest version of the thesis is **empirically defensible on one corpus**: token sprawl surfaces real refactoring candidates, and at least one of them (`FindOptions`) is unambiguous and actionable.

The harder cases (`node`, `content`, `root`) are infrastructure plumbing — frequent but not actionable. **A naïve "this token sprawls, extract a module" rule would mis-fire on these.** The research needs a way to distinguish:

- **Domain sprawl** (refactor candidate) — token appears in N callables; the callables' *other* tokens differ; the shared token is the thing they're each doing something different *to*.
- **Infrastructure sprawl** (not actionable) — token appears in N callables that are otherwise unrelated; the shared token is a threaded value (a Path, a config, an AST node).

The distinguishing signal is probably **co-occurrence shape**:

- `excludes / hidden / ignore / globs / languages` always appear *together* — they are a packet.
- `root` appears with everything, randomly — it is a universal hub.

## Open questions for the next observation

1. Does a co-occurrence index cleanly separate packets from hubs? Predicted yes; needs to be measured.
2. Does the `kernel` token (30 files) form a packet with anything, or is it a free-standing architectural marker?
3. Cross-corpus: does the current `src/slop/` dev tree show measurably lower sprawl for the `find_kernel` packet now that the kernels have been folded? This is the first real before/after experiment.
4. The `_structural` and `rules` packages have such sharp vocabulary signatures that a Jaccard distance between packages might form a useful similarity metric — usable for "which packages overlap meaningfully vs. which are foreign to each other."

## What we need to build next

- **Co-occurrence primitive** on `Lexicon`: per-callable token bundles, then symmetric token-by-token Counter (or graph). Predicted to cleanly surface `FindOptions` as a tight subgraph and `root` as a hub.
- **Cross-corpus comparison helper**: load two roots, compare distributions / sprawl candidates / co-occurrence. Foundation for before/after experiments.
- Eventually: a `slop research dump` subcommand serialising the full distribution + co-occurrence + per-package signature set as JSON for notebook analysis.
