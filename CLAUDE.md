# CLAUDE.md

## What this is

`slop` is built from the bottom up. The foundation is a set of read-only **primitives** an
agent can query for facts, with no thresholds or judgment: a tree-sitter parse (`ast`), an
ownership tree (`scope`), discovery over it (`scope/find.py`: `slop find`, `slop tree`),
identifier statistics (`lexicon`), the import graph (`graph`: `slop deps`), and a
comparison of code names against a canonical vocabulary (`ontology`: `slop vocab`). The
**lint** layer (`rules`, `dispatch`, `violation`) sits on top: a plain linter in which a
rule is a threshold on a measure and a violation is a location, a rule name and one
factual sentence. It is the only place thresholds live. A later, separate **inference**
layer (judgement over what the checks find) is not part of the lint. The target is
an agent that can answer "where is X defined, what is in Y, which names collide, what is
the canonical word for Z" from returned facts alone.

This is the **v3 component-model rebuild** (`slop 3.0.0a0`). The spine is an
ownership tree — **Corpus › Realm › Package › Module › Class › Callable** — carved once
from the parsed sources. A read-only `Structure` view projects over any scope for the
lint layer, and rules consume it. A dispatcher walks the tree and runs each rule at its
declared *altitude*. A rule is kept only if its measure has a published source or is a
standard concept; slop-coined rules were removed (see CHANGELOG).

## Repo layout

The repo root **is** the Python project root (modern src-layout). The former dual tree
(`src/` legacy + `redesign/` active) was collapsed: legacy is deleted, v3 promoted here.

```
slop/                       <- repo root: pyproject.toml, uv.lock, README, LICENSE, NOTICE,
                               CHANGELOG, .slop.toml, docs/, scripts/, .github/
  pyproject.toml            <- name = "agent-slop-lint"; packages = ["src/slop"]; slop = "slop.cli:main"
  src/slop/                 <- the Python package (import slop)
    cli.py                  CLI entry (slop.cli:main): primitives (ast/tree/find/lexicon/deps/vocab/shape),
                              lint layer (lint/check/rules), housekeeping (init/schema/doctor)
    dispatch.py             Dispatcher: altitude-driven rule execution; Report; inline `slop: ignore`
                              suppression; records zero_visited
    violation.py            Violation record (rule, path, line, column, message, value, threshold)
    config.py               AnalysisConfig + RuleConfig (enabled, per-altitude thresholds, params);
                              top-level keys exclude / languages / rules only
    rule.py                 Rule ABC (name, description, altitudes, default_config, check)
    identity.py             ScopeId / ScopeKind / CallableKind / Extent (logical+physical identity)
    span.py                 Span — shared source-location value type
    ast/                    tree-sitter proxy: parse.py, nodes.py (Node), tree.py, grammar/*, paradigm/*
    scope/                  ownership spine: base/aggregate/symbol ABCs, components.py (concrete kinds),
                              carve.py (scan_corpus), context.py (corpus-global graphs/index),
                              identity.py, selection.py (union region), projection.py, lexicon.py (bridge),
                              find.py (discovery: Match, find, outline, collisions)
    lexicon/                standalone linguistic kernel (importable outside the linter):
                              corpus.py (Lexicon), distribution.py (Zipf/hapax), comparison.py
                              (jaccard/containment/cosine/js), tokenize.py, roles.py, stopwords.py
    ontology/               canonical-vocabulary layer: interface.py (Vocabulary ABC, Term, normalize),
                              ir.py (OntologyIR: Open Ontology JSON IR reader), compare.py (matched/unknown/unused)
    lexical/                lexical analysis: coverage.py (coverage(Lexicon, Vocabulary): covered /
                              undefined / unused / unmeasurable, no thresholds); scope/lexicon.py
                              builds the declared-names Lexicon it is fed
    metrics/                slop's measurements over a scope/region:
                              structural/ (view.py + complexity/halstead/ck/cohesion/martin/
                              relational/orphans/hotspots/imports compute), locus.py
                              (narrowest-common-ancestor; duck-typed)
    graph/                  import/dependency graph: build.py, dependency.py, imports.py
    rules/                  12 rules (complexity x3, structure x5, class_design.py: class.* x4) → single flat RULE_REGISTRY (__init__.py)
  tests/                    pytest suite (test_rule_*.py per rule, test_<view>.py, cross-cutting)
```

Every rule declares its `altitudes` (e.g. `{ScopeKind.CORPUS}`) and a `check(component,
rule_config) -> Iterable[Violation]`; the dispatcher invokes it at each component of that
altitude. The `Structure` view is constructed `Structure.over(region)` — a
region is any scope, or a `Selection` union of scopes.

## Setup

```bash
uv sync                       # dev env at repo root (.venv); installs the dev group (pytest, ruff)
./scripts/install.sh          # install `slop` as a uv tool, system-wide
```

## Common commands

Run from the repo root:

```bash
uv run python -m pytest                       # full suite
uv run python -m pytest tests/test_rule_cognitive.py
uv run slop lint --root /path/to/code         # lint any codebase
uv run slop lint --root /path/to/code --output json
uv run slop rules                             # list rules
uv run slop check complexity --root /path     # one family / rule
uv run slop find Store --root /path --output json   # where a name is defined
uv run slop find --collisions --root /path          # names defined more than once
uv run slop tree --root /path --scope pkg --scope-kind package --depth 2
uv run slop vocab --ontology ir.json --root /path   # code names vs canonical vocabulary
```

Note: the `slop` CLI takes `--root` explicitly; the config loader reads only `exclude`,
`languages` and `[rules]` from `.slop.toml` (any other top-level key is a load error).

## Adding a new rule

Signature: `check(component, rule_config) -> Iterable[Violation]`, where `component` is the
scope at the rule's altitude.

1. Create `src/slop/rules/<name>.py` with a `Rule` subclass (`name`, `altitudes`,
   `default_config()`, `check`). Grow a view method on `Structure` for any
   reusable measurement; small rule-only helpers live in the rule module.
2. Register the rule instance in `RULE_REGISTRY` (and `__all__`) in `src/slop/rules/__init__.py`.
3. Config defaults come from the rule's `default_config()` — no separate registry.
4. Tests in `tests/test_rule_<name>.py` (integration) and/or `tests/test_<view>.py`.

`test_config_parity.py` asserts every registered rule round-trips through config.

## Key design decisions

- **Component model, not tool-substrate.** Discovery + ownership live in `scope` (carved
  once); `ast` parses; `metrics`/`lexicon` measure; `rules` threshold + emit. The spine is
  Corpus › Realm › Package › Module › Class › Callable.
- **dispatch-altitude ≠ violation-altitude.** A rule runs at the altitude it needs to
  *compute* (duplication needs the whole corpus to see clone families), but each violation
  is located at the **narrowest scope containing what it is about** (`Violation.at`): the
  entity for a single-entity violation, the first member (by path) of a cycle or clone
  cluster for a group.
- **A rule is a threshold on a measure.** It emits a `Violation` when the measure is
  strictly greater than the limit; the message is one factual sentence naming the unit and
  the number. Nothing else is attached. Suppression is inline
  (`slop: ignore[rule]` on the reported line), applied by the dispatcher. Judgement over
  violations belongs to a later inference layer, not to the rules.
- **Three layers: rule → view method → algorithm helper.** A rule thresholds + emits; a
  view method (`Structure.<m>()`) is the public measurement API; the
  compute lives inline (≤~30 LOC) or in `metrics/<substrate>/<name>.py`.
- **Boundaries** (pinned by `tests/test_layers.py`). `span`, `identity`, `lexicon` and `ast`
  depend on nothing above them (`lexicon`/`ast`: only `slop.span`). `metrics` never imports
  `scope` (views take a duck-typed region), which is why the locus NCA helper lives in
  `metrics/locus.py`. `scope` never imports `rules`, `dispatch`, `cli` or `ontology`; its
  only reach into `metrics`/`graph` is the lazy import in `scope/carve.py` that builds the
  corpus analysis context. `ontology` depends only on `lexicon` and `scope`, and knows
  Open Ontology only through its one reader (`ontology/ir.py`); the rest of slop depends on
  the `Vocabulary` interface. `rules` never imports `cli` or `ontology`.
- **One flat rule registry.** All 12 rules live in `rules/` regardless of substrate;
  `rules/__init__.py` builds a single `RULE_REGISTRY` (substrate grouping encoded nothing the
  imports don't already say).
- **`zero_visited` safeguard.** The dispatcher records each rule's visited-count; a rule
  that examined zero components is listed under `zero_visited` in the JSON report, so "not
  flagged" can be told from "not checked".
- **Config:** thresholds keyed by altitude (validated against the rule's *declared*
  altitudes; a stray key is a load error, not a silent no-op); unknown top-level keys,
  rule keys and params are load errors too.
- **Exit codes:** 0 no violations / 1 any violation / 2 error.

## Release flow

Solo project: `main` = released (PyPI `agent-slop-lint`), `dev` = integration, `feature/*`
off `dev`. A tag push from `main` triggers `.github/workflows/publish.yml`. The repo-root
`README.md` / `LICENSE` are the single source for both GitHub and PyPI (the old src/ copies
are gone, so there is no longer a dual-copy to keep in sync).
