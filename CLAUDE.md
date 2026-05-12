# CLAUDE.md

## What this is

`slop` is an agentic code quality linter. It ships its own discovery primitives (tree-sitter AST, ripgrep, fd, git) and metric kernels, and exposes them through a substrate-aligned package layout (`tree`, `language`, `structure`, `lexicon`, `linter`) with declarative config, threshold checking, and CI exit codes. Self-contained — no external runtime dependency beyond the tree-sitter wheels listed in `pyproject.toml`.

The v2.0 substrate (current `dev`) reorganises by responsibility: a parsed `Tree` of source files feeds two read-only views (`Structure` for code shape, `Lexicon` for identifier vocabulary), which rules consume.

## Repo layout

```
slop/                       <- repo root (docs, LICENSE, NOTICE, README, .slop.toml, .github, scripts)
  src/
    pyproject.toml          <- packages = ["slop"]; scripts: slop = "slop.app:main"
    slop/                   <- the Python package (import slop)
      app.py                Composition root (slop.app:main); delegates to cli.cmd.main
      preflight.py          System-binary dep check (fd, rg, git)
      KERNELS_LICENSE       Apache-2.0 attribution for vendored kernels
      _compat.py            Legacy rule/category name translation (v1.x compat shim)
      cli/                  Argparse + per-command dispatch
        cmd.py              Root parser (lint, check, init, rules, schema, doctor, install)
        _common.py          Shared lint/check runner
        check.py            slop check <target>
        init.py             slop init
        rules.py            slop rules
        schema.py           slop schema
        doctor.py           slop doctor
        color.py            ANSI color helpers with TTY/NO_COLOR detection
        install/
          cmd.py            Root of install subcommand
          hook.py           slop install hook
          skill.py          slop install skill
      config/               Config loading + dataclasses
        loader.py           Upward walk; .slop.toml / pyproject[tool.slop] / defaults
        models.py           SlopConfig, RuleConfig, WaiverConfig
      language/             Grammar hierarchy
        base.py             Language ABC (callable / classes / functions / methods / identifiers / namespaces)
        objectoriented.py,
          procedural.py,
          multipurpose.py   Paradigm subclasses with paradigm-level defaults
        grammars/           Concrete grammars: python, c, cpp, csharp, go, java, javascript, julia, ruby, rust, typescript
      tree/                 Parse substrate
        tree.py             Tree class (formerly Codebase): scan(), walk(), records
        records.py          Scope, Callable, Occurrence, Parameter, ParseResult (frozen dataclasses)
      structure/            Structure view + structural rules
        view.py             Structure(tree, lang): callables(), scopes(), cyclomatic(), …
        rules/__init__.py   STRUCTURAL_RULES (20 entries: structural.* + information.*)
        rules/*.py          per-rule run_X functions (complexity, npath, halstead, …)
      lexicon/              Lexicon view + lexical rules
        view.py             Lexicon(tree, lang): tokens, clusters, first_param_clusters()
        rules/__init__.py   LEXICAL_RULES (9 entries: lexical.*)
        rules/*.py          per-rule run_X (stutter, verbosity, cowards, hammers, …)
      linter/               Linter, Result, Slop, dispatch, format, cross-cutting rules
        linter.py           Linter(config).run() — main entry point
        _dispatch.py        select_rules, apply_waivers, overall_status, execute_rule
        _shim.py            legacy_v2_shim — adapts (root, rc, sc) → (view, rc, sc)
        result.py           Result dataclass; .json() returns dict, .pretty() returns str
        slop.py             Slop finding type (formerly Violation)
        types.py            RuleResult, RuleDefinition, RuleRunner
        format.py           Human / quiet / dict formatters (delegated to by Result)
        __init__.py         Aggregates STRUCTURAL_RULES + LEXICAL_RULES + CROSS_CUTTING_RULES
                              → RULE_REGISTRY, RULES_BY_NAME, RULES_BY_CATEGORY, CATEGORIES
        rules/__init__.py   CROSS_CUTTING_RULES (2: structural.hotspots, structural.orphans)
        rules/hotspots.py,
          rules/dead_code.py
      schemas/              IO schema generation (config JSON Schema)
      _ast/                 (legacy) AST-query primitives (tree-sitter loaders)
      _fs/                  (legacy) Filesystem-discovery primitives (fd)
      _text/                (legacy) Token-level search primitives (ripgrep)
      _compose/             (legacy) Cross-tool primitives: usages, hotspots, prune, git
      _structural/          (legacy) Structural metric kernels: ccx, ck, npath, halstead, deps, robert
      _lexical/             (legacy) Lexical metric kernels: stutter, sprawl, imposters, …
      _util/                (legacy) Subprocess wrappers, install doctor
      _skill/               Bundled skill (SKILL.md + scripts) for `slop install skill`
    tests/
      test_v2/              New-substrate tests (Tree, Language, Structure, Lexicon, Linter, Result)
      test_rules/           Per-rule integration tests
      test_*.py             Cross-cutting tests (config, output, …)
```

The `_ast`, `_fs`, `_text`, `_compose`, `_structural`, `_lexical`, `_util` packages are **legacy kernels**: 29 of 31 rules still call into them via `legacy_v2_shim`. They retire per-rule as each rule's logic moves natively onto its view (`Structure.cyclomatic` and `Lexicon.first_param_clusters` are the only two view methods so far).

## Setup

```bash
# Full install (slop as a uv tool, available system-wide)
./scripts/install.sh

# Development only (local venv under src/)
cd src && uv sync
```

## Common commands

All dev commands run from `src/`:

```bash
cd src

# Run all tests
uv run python -m pytest

# Run the new-substrate tests only
uv run python -m pytest tests/test_v2

# Lint (against any codebase)
uv run slop lint --root /path/to/code

# List rules
uv run slop rules

# Run one category or rule
uv run slop check structural.complexity --root /path/to/code
```

## Adding a new rule

The v2.0 rule signature is `(view, rule_config, slop_config) -> RuleResult` where `view` is a `Structure` or `Lexicon` instance.

1. Decide the substrate: structural metric → `slop/structure/rules/`; lexical/naming → `slop/lexicon/rules/`; cross-cutting (needs git history or whole-tree analysis) → `slop/linter/rules/`.
2. Create `<substrate>/rules/<name>.py` with `run_<rule>(view, rule_config, slop_config) -> RuleResult`. If the logic still calls a legacy kernel, wrap with `legacy_v2_shim(run_<rule>)` at registry time; otherwise grow a view method on `Structure` / `Lexicon` and call it directly.
3. Append a `RuleDefinition` to `STRUCTURAL_RULES` / `LEXICAL_RULES` / `CROSS_CUTTING_RULES` in the substrate's `rules/__init__.py`. (Aggregation at `slop.linter.RULE_REGISTRY` is automatic.)
4. Add default config in `slop/config/loader.py` (`DEFAULT_RULE_CONFIGS`).
5. Add to the generated config template in `slop/config/loader.py` (`generate_default_config`).
6. Write tests in `src/tests/test_rules/test_<name>.py` (integration) and/or `src/tests/test_v2/test_<view>.py` (view-method unit tests).

Rules emit `Slop` (the finding type, importable from `slop.linter`) for threshold breaches.

## Key design decisions

- **Substrate-aligned packages, not tool-substrate.** Discovery and metric logic is split by responsibility (`tree` parses, `structure`/`lexicon` view, `linter` dispatches), not by the underlying tool. Legacy kernels (`slop._fs`, `slop._text`, `slop._ast`, `slop._compose`, `slop._structural`, `slop._lexical`, `slop._util`) survive the cutover as the implementation behind 29 of 31 rules; they retire per-rule as views grow. The kernel tree is Apache-2.0; see `src/slop/KERNELS_LICENSE` and the repo-root `NOTICE`.
- **Per-substrate rule registries, aggregated at the linter.** `slop.structure.rules.STRUCTURAL_RULES`, `slop.lexicon.rules.LEXICAL_RULES`, and `slop.linter.rules.CROSS_CUTTING_RULES` each own their substrate's rules; `slop.linter.RULE_REGISTRY` concatenates them. No central `slop.rules` module.
- **`cmd.py` convention.** Every CLI sub-package's root command lives in `<pkg>/cmd.py` (e.g. `slop/cli/cmd.py`, `slop/cli/install/cmd.py`).
- **`Result.json()` returns a dict; `Result.pretty()` returns a string.** Both delegate to `slop.linter.format`. The CLI does `json.dumps(result.json(), indent=2)` at the output boundary.
- **Config discovery walks upward** from CWD for `.slop.toml` or `pyproject.toml` with `[tool.slop]`. A pyproject without `[tool.slop]` is skipped, so sub-project pyproject files (like `src/pyproject.toml` in this repo) don't mask a repo-root `.slop.toml`.
- **14-day default hotspot window.** Tuned for agentic code generation where architectural damage accumulates in days, not months.
- **Exit codes:** 0 = clean, 1 = violations, 2 = error.

## v2.0 cutover notes (still load-bearing on `dev`)

- CLI entry: `slop.app:main` (not `slop.cli:main`).
- `slop.engine`, `slop.models`, `slop.output`, `slop.rules` are gone. Use `slop.linter.linter.Linter`, `slop.config.models`, `slop.linter.types`, `slop.linter.format`, and `slop.linter.RULE_REGISTRY` respectively.
- `Violation` → `Slop`; `LintResult` → `Result`. No alias compatibility retained.
- `SLOP_ENGINE=v2` env var no longer has any effect (removed; v2 is the only path).
- `RuleDefinition.run_v2` slot removed; single `run` slot accepts `(view, rc, sc)`.

## README/LICENSE duplication

`README.md` and `LICENSE` are tracked in two places: the repo root (for GitHub's landing page) and `src/` (for PyPI, via hatchling). Hatchling validates the `readme` and `license-files` paths against the pyproject directory before applying force-include, so it will not accept `../README.md`-style paths. When updating either file, update both copies. If this drift becomes painful, add a pre-commit hook or CI check that fails when `src/README.md` and `README.md` (or the two `LICENSE` files) disagree.
