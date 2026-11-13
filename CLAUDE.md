# CLAUDE.md

`slop` is a linter plus a code-structure query tool. The repo root is the Python project
root (src-layout; package `agent-slop-lint`, import `slop`, CLI `slop.cli:main`).

## Layers

- `src/slop/ast/`: tree-sitter parse (`parse.py`, `nodes.py`, `tree.py`, `grammar/`, `paradigm/`).
- `src/slop/scope/`: ownership tree Corpus › Realm › Package › Module › Class › Callable,
  carved once from the parse (`carve.py`); `discover.py` lists the files to read;
  `descendants.py` is the one walk over a scope's children (`_iter_callables`, `_iter_modules`); `find.py`
  is name discovery (`slop find`, `slop tree`).
- `src/slop/metrics/`: measures over a scope. `Structure.over(region)` in
  `metrics/structural/view.py` is the view rules and commands read.
  `Structure.hotspots` backs `slop hotspots`; no rule reads it.
- `src/slop/graph/`: module import graph (`slop deps`).
- `src/slop/lexicon/`, `src/slop/lexical/`: identifier statistics and coverage against a
  vocabulary (`slop lexicon`).
- `src/slop/ast/binding.py`: name binding (what each name refers to) from the per-grammar locals
  queries in `ast/grammar/locals/*.scm`; read through `Component.bindings()`.
- `src/slop/ontology/`: the project's vocabulary (`.slop/ontology.json`, SKOS terms: one word,
  its definition, alt/hidden labels, broader/related); `model.py`, `fs.py`, `check.py`,
  `draft.py` (seed from declared words), `occurrence.py` (where a word reaches the code, rename
  plans). It reaches lint through the `lexicon.Vocabulary` protocol on the analysis context.
- Lint layer: `rule.py` (Rule), `rules/` (15 rules, `RULE_REGISTRY` in `rules/__init__.py`),
  `dispatch.py`, `violation.py`, `config.py`.
- `src/slop/skill/`: the one Agent Skill, `slop`, built at install time from the sources it
  describes (`slop skill list | show | install`); its capabilities table is tested against the parser. `layout.py` holds file names more than one package uses.
- `cli/`: the commands, one module per command family; each `register`s its subcommands with
  `__init__.parser()`, and `resolve.py`/`render.py` hold the shared `--root`/`--scope`/`--output`
  handling. `tests/`: pytest, `test_rule_*.py` per rule.

## Commands

```bash
uv sync                                       # dev env (pytest, ruff)
uv run python -m pytest                       # full suite
uv run python -m pytest tests/test_rule_cognitive.py
uv run slop lint --root src                   # lint this repo
uv run slop rules
```

## Rule contract

- A `Rule` declares `name`, `description`, `altitudes` (a set of `ScopeKind`),
  `default_options` (its flat options and their defaults; `default_config()` builds the
  `RuleConfig` from them) and
  `check(component, config) -> Iterable[Violation]`. The dispatcher
  calls `check` once per component at each declared altitude; a rule never walks the corpus.
- A `Limit` (`rules/limit.py`) is a rule that compares one measure with its `limit` option. A subclass sets `altitude` and `default_limit` and implements
  `measure(view)` and `describe(...)`. A violation needs the measure strictly greater than
  the limit.
- The measure lives on `Structure` or in `metrics/`, not in the rule.
- `Violation(rule, path, line, column, message, value, threshold)`; `Violation.at(component,
  ...)` locates it at the narrowest scope the violation is about. A rule runs at the
  altitude it needs to compute (duplication runs at corpus) but reports at the entity or the
  first member (by path) of a group. The message is one factual sentence naming the unit
  and the number.
- Add a rule: write `src/slop/rules/<name>.py`, add an instance to `RULE_REGISTRY`, add
  `tests/test_rule_<name>.py`.

## Invariants

- Config top-level keys are `exclude` and `rules` only; unknown keys, rules and options, and
  wrongly typed values, are load errors. Every command loads through
  `AnalysisConfig.load`. `slop check RULE...` runs the named rules even when disabled.
- A violation is *objective* or *subjective*. Objective: it follows from syntax and a stated
  limit alone, so no idiom or intent excuses it. Subjective: it depends on what the author
  meant (a mask, a unit conversion, a format offset). A rule with `subjective = True` reports
  WARN lines, kept in `Report.warnings`; only objective violations exit 1. Never add
  exemptions or special cases to make a subjective case objective; the inferential layer,
  which is not built, will judge warnings.
- A noisy rule is one of: (a) valid and just large, keep it; (b) broken, fix the measure
  (`duplicate-code` once matched shapes whose names differed; it now keeps every name except those the body binds); (c) trying to decide
  a subjective case, mark it `subjective = True`. Classify findings by hand on slop's own
  source and on another corpus before choosing, and record the rate in the rule's docstring.
- Exit codes: lint `0` no violations (warnings allowed) / `1` any violation / `2` error. Read-only commands `0`
  answered / `2` could not answer; an empty answer carries caveats.
- Suppression is inline `slop: ignore[exact-rule-name]`, applied by the dispatcher. The dispatcher
  lists rules that visited no component under `zero_visited` in the JSON report.
- Layer imports are pinned by `tests/test_layers.py`: `span`, `identity`, `lexicon`, `ast`
  depend on nothing above them; `metrics` never imports `scope`; `scope` never imports
  `rules`, `dispatch`, `cli` or `ontology`; `rules` never imports `cli` or `ontology`.
- Every rule traces to a published measure or a standard concept; cite it in the rule's
  docstring and in `NOTICE`.

## Release

`main` is released (tag push triggers `.github/workflows/publish.yml`), `dev` is integration.
`README.md` and `LICENSE` at the root serve both GitHub and PyPI.
