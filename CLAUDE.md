# CLAUDE.md

## What this is

`slop` is an agentic code-quality linter built for the agentic era: its job is surfacing
the structural debt humans let pass in agent-generated code, not the style smells agents
self-correct. It ships its own discovery primitives (tree-sitter AST, ripgrep, fd, git)
and metric kernels — self-contained beyond the tree-sitter wheels in `pyproject.toml`.

This is the **v3 component-model rebuild** (`slop 3.0.0a0`). The spine is an
ownership tree — **Corpus › Realm › Package › Module › Class › Callable** — carved once
from the parsed sources. Two read-only views project over any scope (`Structure` for code
shape, `Lexical` for naming/vocabulary), and rules consume them. A dispatcher walks the
tree and runs each rule at its declared *altitude*.

## Repo layout

The repo root **is** the Python project root (modern src-layout). The former dual tree
(`src/` legacy + `redesign/` active) was collapsed: legacy is deleted, v3 promoted here.

```
slop/                       <- repo root: pyproject.toml, uv.lock, README, LICENSE, NOTICE,
                               CHANGELOG, .slop.toml, docs/, scripts/, .github/
  pyproject.toml            <- name = "agent-slop-lint"; packages = ["src/slop"]; slop = "slop.cli:main"
  src/slop/                 <- the Python package (import slop)
    cli.py                  CLI entry (slop.cli:main): lint / check / rules / init / schema
    dispatch.py             Dispatcher — altitude-driven rule execution; records zero_visited
    finding.py              Finding ontology: Verdict / Observation / Evidence / Action / Severity / Disposition
    config.py               AnalysisConfig + RuleConfig (per-altitude thresholds, scope-keyed ignore)
    rule.py                 Rule ABC (name, altitudes, default_config, check)
    identity.py             ScopeId / ScopeKind / CallableKind / Extent (logical+physical identity)
    span.py                 Span — shared source-location value type
    ast/                    tree-sitter proxy: parse.py, nodes.py (Node), tree.py, grammar/*, paradigm/*
    scope/                  ownership spine: base/aggregate/symbol ABCs, components.py (concrete kinds),
                              carve.py (scan_corpus), context.py (corpus-global graphs/index),
                              identity.py, selection.py (union region), projection.py, lexicon.py (bridge)
    lexicon/                standalone linguistic kernel (importable outside the linter):
                              corpus.py (Lexicon), distribution.py (Zipf/hapax), comparison.py
                              (jaccard/containment/cosine/js), tokenize.py, roles.py, stopwords.py
    metrics/                slop's measurements over a scope/region:
                              structural/ (view.py + complexity/halstead/ck/martin/relational/
                              orphans/hotspots/imports compute), lexical/ (view.py + affix/clusters/
                              profile), locus.py (narrowest-common-ancestor; duck-typed)
    graph/                  import/dependency graph: build.py, dependency.py, imports.py
    rules/                  one rule per file → single flat RULE_REGISTRY (__init__.py);
                              _battery.py and _<helper>.py hold rule-internal shared logic
  tests/                    pytest suite (test_rule_*.py per rule, test_<view>.py, cross-cutting)
```

Every rule declares its `altitudes` (e.g. `{ScopeKind.CORPUS}`) and a `check(component,
rule_config) -> Iterable[Finding]`; the dispatcher invokes it at each component of that
altitude. Views are constructed `Structure.over(region)` / `Lexical.over(region)` — a
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
uv run python -m pytest tests/test_rule_cohesion.py
uv run slop lint --root /path/to/code         # lint any codebase
uv run slop lint --root /path/to/code --output json
uv run slop rules                             # list rules
uv run slop check complexity --root /path     # one family / rule
```

Note: the `slop` CLI takes `--root` explicitly; the config loader reads only `[rules]`
and `[ignore]` from `.slop.toml` (it does **not** read a `root` / `languages` key).

## Adding a new rule

Signature: `check(component, rule_config) -> Iterable[Finding]`, where `component` is the
scope at the rule's altitude.

1. Create `src/slop/rules/<name>.py` with a `Rule` subclass (`name`, `altitudes`,
   `default_config()`, `check`). Grow a view method on `Structure` / `Lexical` for any
   reusable measurement; small rule-only helpers live in the rule module or `rules/_<helper>.py`.
2. Register the rule instance in `RULE_REGISTRY` (and `__all__`) in `src/slop/rules/__init__.py`.
3. Config defaults come from the rule's `default_config()` — no separate registry.
4. Tests in `tests/test_rule_<name>.py` (integration) and/or `tests/test_<view>.py`.

`test_config_parity.py` asserts every registered rule round-trips through config.

## Key design decisions

- **Component model, not tool-substrate.** Discovery + ownership live in `scope` (carved
  once); `ast` parses; `metrics`/`lexicon` measure; `rules` threshold + emit. The spine is
  Corpus › Realm › Package › Module › Class › Callable.
- **dispatch-altitude ≠ finding-altitude.** A rule runs at the altitude it needs to
  *compute* (stutter needs the whole corpus to see token sharing), but each finding
  attributes to the **narrowest scope containing what it is about** — the entity for a
  single-entity finding, the narrowest common ancestor (`metrics/locus.py`) for a group.
  Records carry a canonical `ScopeId` locus; nothing collapses onto the corpus root.
- **Finding ontology — Verdict vs Observation, driven by epistemic certainty.** A
  `Verdict` is a defect with a prescribable fix (or `REVIEW`: confident pattern, deferred
  remedy, WARNING-capped). An `Observation` is a claim-free evidential nudge (pinned INFO /
  INVESTIGATE; no prescription — it makes no precision claim, so it cannot be a false
  positive). The disposition policy: **exact** pattern → directive verdict; **certain
  pattern, open remedy** → REVIEW; **inferred** pattern → observation, or REVIEW *only when
  an independent signal corroborates* (a battery, see `rules/_battery.py`). This cuts
  across substrate — `redundancy` is structural but soft; `stutter` is lexical but exact.
- **Three layers: rule → view method → algorithm helper.** A rule thresholds + emits; a
  view method (`Structure.<m>()` / `Lexical.<m>()`) is the public measurement API; the
  compute lives inline (≤~30 LOC) or in `metrics/<substrate>/<name>.py`.
- **Boundaries.** `lexicon` is a standalone kernel (imports only `slop.span` + stdlib).
  `metrics` never imports `scope` (views take a duck-typed region); `scope` never imports
  `metrics`/`rules`/`linter`. The locus NCA helper lives in `metrics/locus.py` for this reason.
- **One flat rule registry.** All 25 rules live in `rules/` regardless of substrate;
  `rules/__init__.py` builds a single `RULE_REGISTRY` (substrate grouping encoded nothing the
  imports don't already say).
- **`zero_visited` safeguard.** The dispatcher records each rule's visited-count; a rule
  that examined zero components surfaces as `zero_visited`, so "not flagged" is verifiably
  clean rather than silently broken.
- **Config:** thresholds keyed by altitude (validated against the rule's *declared*
  altitudes — a stray key is a load error, not a silent no-op). Exemptions are scope-keyed
  `ignore` lists matched on the finding's canonical `ScopeId` (kind + qualname).
- **Exit codes:** 0 clean / 1 any ERROR-severity verdict / 2 error.

## Release flow

Solo project: `main` = released (PyPI `agent-slop-lint`), `dev` = integration, `feature/*`
off `dev`. A tag push from `main` triggers `.github/workflows/publish.yml`. The repo-root
`README.md` / `LICENSE` are the single source for both GitHub and PyPI (the old src/ copies
are gone, so there is no longer a dual-copy to keep in sync).
