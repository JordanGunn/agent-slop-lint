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
        _templates.py       `.slop.toml` template emission for `slop init`: PROFILES catalog + generate_default_config()
      config/               Config-file domain (slop.config) — load, validate, model; no scaffold emission
        __init__.py         Public surface: Config, Waiver, load_config, schema
        models.py           Config + Waiver dataclasses
        loader.py           Upward walk (.slop.toml / pyproject[tool.slop]) + merge + DEFAULT_RULE_CONFIGS
        schema/v1.json      JSON Schema asset — committed source of truth for the config-file shape
        schema/__init__.py  load(version="v1") helper (importlib.resources)
      language/             Grammar hierarchy
        base.py             Language ABC (callable / classes / functions / methods / identifiers / namespaces)
        objectoriented.py,
          procedural.py,
          multipurpose.py   Paradigm subclasses with paradigm-level defaults
        grammars/           Concrete grammars: python, c, cpp, csharp, go, java, javascript, julia, ruby, rust, typescript
        _grammars.py        load_language / detect_language (tree-sitter package loader + extension map)
      tree/                 Parse substrate
        tree.py             Tree class: scan(), walk(), records
        records.py          Scope, Callable, Occurrence, Parameter, ParseResult (frozen dataclasses)
        _parse.py           parse_file (tree-sitter parser wrapper)
        _find.py            find_kernel (fd file-discovery wrapper)
      structure/            Structure view + structural rules
        view.py             Structure(tree, lang): callables(), scopes(), cyclomatic(), …
        rules/__init__.py   STRUCTURAL_RULES (per-rule run_X functions)
        rules/*.py          complexity, npath, halstead, class_metrics, packages, etc.
        _grep.py            ripgrep wrapper (used by _orphans)
        _git.py             git log --numstat wrapper (used by _hotspots)
      lexicon/              Lexicon view + lexical rules
        view.py             Lexicon: tokens, named_entities, first_param_clusters, …
        records.py          NamedEntity, FirstParameterCluster
        _affix.py           Token-Levenshtein + alphabet clustering + FCA + Lexeme + UNIVERSAL_NOISE
        _profile.py         Multi-signal cluster classifier (body Jaccard, receiver-call density)
        rules/__init__.py   LEXICAL_RULES (stutter, verbosity, cowards, hammers, tautology, sprawl, imposters, slackers, confusion)
      linter/               Linter, Result, Slop, dispatch, format, cross-cutting rules
        linter.py           Linter(config).run() — main entry point
        _dispatch.py        select_rules, apply_waivers, overall_status, execute_rule
        result.py           Result dataclass; .json() returns dict, .pretty() returns str
        slop.py             Slop finding type
        types.py            RuleResult, RuleDefinition, RuleRunner
        format.py           Human / quiet / dict formatters (delegated to by Result)
        __init__.py         Aggregates STRUCTURAL_RULES + LEXICAL_RULES + CROSS_CUTTING_RULES
                              → RULE_REGISTRY, RULES_BY_NAME, RULES_BY_CATEGORY, CATEGORIES
        rules/__init__.py   CROSS_CUTTING_RULES (hotspots, orphans)
        rule_config.py      Per-rule RuleConfig dataclass — rule-domain (config files populate it; semantics belong here)
        severity.py         Severity enum — rule-domain
        tags.py             Rule namespace vocabulary (Tag) + Scope enum
      preflight.py          System-binary dep check (fd, rg, git)
      _doctor.py            Doctor primitives used by preflight + cli/doctor
      _subprocess.py        run_tool / which subprocess wrappers (used by _grep, _git, _find, _doctor)
      _skill/               Bundled skill (SKILL.md + scripts) for `slop install skill`
    tests/
      test_v2/              New-substrate tests (Tree, Language, Structure, Lexicon, Linter, Result)
      test_rules/           Per-rule integration tests
      test_*.py             Cross-cutting tests (config, output, …)
```

Every rule now consumes its substrate's view directly (`Structure` or `Lexicon`); the v1.x legacy-kernel underscore-packages (`_ast`, `_fs`, `_text`, `_compose`, `_structural`, `_lexical`, `_util`) and the `legacy_v2_shim` adapter have all been retired. Infrastructure primitives (tree-sitter wrapper, fd, ripgrep, git, subprocess) live under their substrate's private modules (`tree/_parse.py`, `tree/_find.py`, `structure/_grep.py`, `structure/_git.py`, `_subprocess.py`).

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
uv run slop check complexity --root /path/to/code
```

## Adding a new rule

The v2.0 rule signature is `(view, rule_config, slop_config) -> RuleResult` where `view` is a `Structure` or `Lexicon` instance.

1. Decide the substrate: structural metric → `slop/structure/rules/`; lexical/naming → `slop/lexicon/rules/`; cross-cutting (needs git history or whole-tree analysis) → `slop/linter/rules/`.
2. Create `<substrate>/rules/<name>.py` with `run_<rule>(view, rule_config, slop_config) -> RuleResult`. Grow a view method on `Structure` / `Lexicon` for any reusable compute; small rule-specific helpers can live in the rule module.
3. Append a `RuleDefinition` to `STRUCTURAL_RULES` / `LEXICAL_RULES` / `CROSS_CUTTING_RULES` in the substrate's `rules/__init__.py`. (Aggregation at `slop.linter.RULE_REGISTRY` is automatic.)
4. Add default config in `slop/config/loader.py` (`DEFAULT_RULE_CONFIGS`).
5. Add to the generated config template in `slop/cli/_templates.py` (`generate_default_config`).
6. Write tests in `src/tests/test_rules/test_<name>.py` (integration) and/or `src/tests/test_v2/test_<view>.py` (view-method unit tests).

Rules emit `Slop` (the finding type, importable from `slop.linter`) for threshold breaches.

## Key design decisions

- **Substrate-aligned packages, not tool-substrate.** Discovery and metric logic is split by responsibility (`tree` parses, `structure`/`lexicon` view, `linter` dispatches), not by the underlying tool. Each substrate owns its private infrastructure modules (`_parse`, `_find`, `_grep`, `_git`, etc.). The original kernel tree is Apache-2.0; see `src/slop/KERNELS_LICENSE` and the repo-root `NOTICE`.
- **Per-substrate rule registries, aggregated at the linter.** `slop.structure.rules.STRUCTURAL_RULES`, `slop.lexicon.rules.LEXICAL_RULES`, and `slop.linter.rules.CROSS_CUTTING_RULES` each own their substrate's rules; `slop.linter.RULE_REGISTRY` concatenates them. No central `slop.rules` module.
- **`cmd.py` convention.** Every CLI sub-package's root command lives in `<pkg>/cmd.py` (e.g. `slop/cli/cmd.py`, `slop/cli/install/cmd.py`).
- **`Result.json()` returns a dict; `Result.pretty()` returns a string.** Both delegate to `slop.linter.format`. The CLI does `json.dumps(result.json(), indent=2)` at the output boundary.
- **Config discovery walks upward** from CWD for `.slop.toml` or `pyproject.toml` with `[tool.slop]`. A pyproject without `[tool.slop]` is skipped, so sub-project pyproject files (like `src/pyproject.toml` in this repo) don't mask a repo-root `.slop.toml`.
- **Config schema is a versioned JSON asset, not a Python function.** `slop/config/schema/v1.json` is the committed source of truth; `slop schema [--version v1]` reads it via `importlib.resources`. A pytest drift guard (`tests/test_config_schema.py`) asserts the asset stays in sync with `Config` dataclass fields and `DEFAULT_RULE_CONFIGS` keys — adding a rule without updating the schema fails CI.
- **Config-domain vs. rule-domain split.** `slop.config` owns config-file shape: `Config`, `Waiver`, the TOML loader, the schema asset. `slop.linter.rule_config`, `slop.linter.severity`, `slop.linter.tags` stay in `linter/` — they're rule settings the config file *populates*, not config-file shape.
- **14-day default hotspot window.** Tuned for agentic code generation where architectural damage accumulates in days, not months.
- **Exit codes:** 0 = clean, 1 = violations, 2 = error.

## v2.0 cutover notes (still load-bearing on `dev`)

- CLI entry: `slop.app:main` (not `slop.cli:main`).
- `slop.engine`, `slop.models`, `slop.output`, `slop.rules`, `slop.schemas` are gone. Use `slop.linter.linter.Linter`, `slop.config.models`, `slop.linter.types`, `slop.linter.format`, `slop.linter.RULE_REGISTRY`, and `slop.config.schema` respectively.
- `Violation` → `Slop`; `LintResult` → `Result`. No alias compatibility retained.
- `SLOP_ENGINE=v2` env var no longer has any effect (removed; v2 is the only path).
- `RuleDefinition.run_v2` slot removed; single `run` slot accepts `(view, rc, sc)`.
- `slop._compat` (v1→v2 rule-name translation) is retired. v2 rule names are the only accepted names; old config keys silently no-op.

## README/LICENSE duplication

`README.md` and `LICENSE` are tracked in two places: the repo root (for GitHub's landing page) and `src/` (for PyPI, via hatchling). Hatchling validates the `readme` and `license-files` paths against the pyproject directory before applying force-include, so it will not accept `../README.md`-style paths. When updating either file, update both copies. If this drift becomes painful, add a pre-commit hook or CI check that fails when `src/README.md` and `README.md` (or the two `LICENSE` files) disagree.
