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
      doctor.py             Doctor primitives used by preflight + cli/doctor
      shell.py              run_tool / which subprocess wrappers
      KERNELS_LICENSE       Apache-2.0 attribution for vendored kernels
      cli/                  Argparse + per-command dispatch
        cmd.py              Root parser (lint, check, init, rules, schema, doctor, install)
        common.py           Shared lint/check runner + register_subcommand helper
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
        templates.py       `.slop.toml` template emission for `slop init`: PROFILES catalog + generate_default_config()
      config/               Config-file domain (slop.config) — load, validate, model; no scaffold emission
        __init__.py         Public surface: Config, load_config, schema
        config.py           Config dataclass (incl. global scope-keyed `ignore`)
        loader.py           Upward walk (.slop.toml / pyproject[tool.slop]) + merge + DEFAULT_RULE_CONFIGS
        schema/v1.json      JSON Schema asset — committed source of truth for the config-file shape
        schema/__init__.py  load(version="v1") helper (importlib.resources)
      language/             Grammar hierarchy
        base.py             Language ABC (callable / classes / functions / methods / identifiers / namespaces)
        objectoriented.py,
          procedural.py,
          multipurpose.py   Paradigm subclasses with paradigm-level defaults
        grammars/           Concrete grammars: python, c, cpp, csharp, go, java, javascript, julia, ruby, rust, typescript
        treesitter.py       load_language / detect_language (tree-sitter package loader + extension map)
      tree/                 Parse substrate
        tree.py             Tree class: scan(), walk(), records
        records.py          Scope, Callable, Occurrence, Parameter, ParseResult (frozen dataclasses)
        parse.py            parse_file (tree-sitter parser wrapper)
        find.py             find_kernel (fd file-discovery wrapper)
      structure/            Structure view + view-internal helpers
        view.py             Structure(tree, lang): callables(), scopes(), cyclomatic(), redundancy(), … (thin facade for non-trivial metrics)
        records.py          RedundancyPair, etc. — public records emitted by view methods
        annotations.py     Annotation/escape-hatch density compute
        clones.py          Type-2 clone detection compute
        hidden_mutators.py Hidden-mutator parameter detection compute
        hotspots.py        Churn × complexity compute (Tornhill 2015)
        imports.py         Import-graph + dependency-cycle compute
        orphans.py         Whole-tree orphan symbol detection compute
        packages.py        Robert C. Martin package-level (rigidity / uselessness) compute
        redundancy.py      Sibling-callee overlap compute
        sentinels.py       String sentinel detection compute
        git.py             git log --numstat wrapper (used by hotspots)
        grep.py            ripgrep wrapper (used by orphans)
      lexicon/              Lexicon view + view-internal helpers + public utility modules
        view.py             Lexicon: tokens, named_entities, first_param_clusters, … (thin facade for non-trivial methods)
        records.py          NamedEntity, FirstParameterCluster
        affix.py            Public: Token-Levenshtein + alphabet clustering + FCA + Lexeme + UNIVERSAL_NOISE — imported directly by rules and tests
        actions.py          Public: action-name vocabulary primitives
        filters.py          Public: token-filter primitives
        profile.py         Multi-signal cluster classifier (body Jaccard, receiver-call density) — view-internal
        diagnostics.py      Research-grade cell/cluster diagnostics (not yet productionised)
      linter/               Linter, Result, Slop, dispatch, format, rule registry
        linter.py           Linter(config).run() — main entry point
        dispatch.py         select_rules, apply_ignores, overall_status, execute_rule
        result.py           Result dataclass; .json() returns dict, .pretty() returns str
        slop.py             Slop finding type
        types.py            RuleResult, RuleDefinition, RuleRunner
        format.py           Human / quiet / dict formatters (delegated to by Result)
        rule_config.py      Per-rule RuleConfig dataclass
        severity.py         Severity enum
        tags.py             Rule namespace vocabulary (Tag) + Scope enum
        __init__.py         Lazy-loads RULE_REGISTRY / RULES_BY_NAME / RULES_BY_CATEGORY / CATEGORIES from .rules
        rules/__init__.py   Single flat RULE_REGISTRY built from every rule module's RULE constant
        rules/*.py          One rule per file: complexity.cyclomatic, lexical.stutter, hotspots, etc. (30 rules total; most emit verdicts, `vocabulary` emits an observation)
        rules/<helper>.py    Rule-internal shared helpers (complexity_dispatch, class_index, architecture, halstead)
      skill/                Bundled skill (SKILL.md + scripts) for `slop install skill`
    tests/
      test_v2/              New-substrate tests (Tree, Language, Structure, Lexicon, Linter, Result)
      test_rules/           Per-rule integration tests
      test_*.py             Cross-cutting tests (config, output, …)
```

Every rule consumes its substrate's view directly (`Structure` or `Lexicon`), declared via `RuleDefinition.view`; the dispatcher passes `getattr(tree, view)`. The rare cross-view rule declares `view="tree"` and receives the whole `Tree` (both views) — currently only `vocabulary`, which correlates lexical concept ownership with the structural import graph. The v1.x legacy-kernel underscore-packages have all been retired. Infrastructure primitives (tree-sitter wrapper, fd, ripgrep, git, subprocess) live under their substrate's modules (`tree/parse.py`, `tree/find.py`, `structure/grep.py`, `structure/git.py`, root-level `shell.py`).

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

The rule signature is `(view, rule_config, slop_config) -> RuleResult` where `view` is a `Structure` or `Lexicon` instance.

1. Create `slop/linter/rules/<name>.py` with `run_<rule>(view, rule_config, slop_config) -> RuleResult`. Grow a view method on `Structure` / `Lexicon` for any reusable measurement compute; small rule-specific helpers can live in the rule module or in a `slop/linter/rules/_<helper>.py`.
2. Define `RULE: RuleDefinition = RuleDefinition(...)` at module bottom.
3. Add the module to the imports and the `RULE_REGISTRY` list in `slop/linter/rules/__init__.py`.
4. Add default config in `slop/config/loader.py` (`DEFAULT_RULE_CONFIGS`).
5. Add to the generated config template in `slop/cli/templates.py` (`generate_default_config`).
6. Write tests in `src/tests/test_rules/test_<name>.py` (integration) and/or `src/tests/test_v2/test_<view>.py` (view-method unit tests).

Rules emit `Slop` (the finding type, importable from `slop.linter`) for threshold breaches.

## Key design decisions

- **Substrate-aligned packages, not tool-substrate.** Discovery and metric logic is split by responsibility (`tree` parses, `structure`/`lexicon` view, `linter` dispatches), not by the underlying tool. Each substrate owns its private infrastructure modules (`parse`, `find`, `grep`, `git`, etc.). The original kernel tree is Apache-2.0; see `src/slop/KERNELS_LICENSE` and the repo-root `NOTICE`.
- **Metric vs. rule, structural separation.** A *metric* is the measurement (`Structure.cyclomatic()`, `Lexicon.first_param_clusters()`) — it lives as a method on the view. A *rule* is the threshold check + Slop emission that consumes that metric — it lives in `slop/linter/rules/`. The substrate package contains views; the linter package contains rules. The two are distinct concerns at the package level.
- **One flat rule registry.** All rules live in `slop/linter/rules/` regardless of which view they consume; `slop/linter/rules/__init__.py` builds a single `RULE_REGISTRY` from each module's `RULE` constant. Directory grouping by substrate was vestigial from the retired `structural.*` / `lexical.*` name prefixes — without those prefixes, the substrate grouping encodes nothing the rule's imports don't already say.
- **Verdicts vs. observations (`Slop.disposition`).** A finding is either a `VERDICT` (a threshold-gated defect carrying the corrective triple `action`/`prescription`/`confidence`; counts toward the violation/advisory tally and can fail the build) or an `OBSERVATION` (a claim-free empirical nudge carrying `Evidence` + a natural-language `message`; `action` is `INVESTIGATE`, no prescription, `info` severity, never affects the verdict). Observations live in `RuleResult.observations`, not `violations`, so they never render as defects. The point: where slop can measure something useful but can't honestly prescribe a remedy (e.g. the identifier token distribution is a Zipf near-invariant, so no scalar threshold is honest), it emits the evidence and lets the consuming agent decide — an observation makes no precision claim, so it cannot be a false positive. First instance: the `vocabulary` rule (`Lexicon.token_distribution()` → `TokenDistribution.narrate()`).
- **Three layers, not duplication: rule → view method → algorithm helper.** A rule (`slop/linter/rules/<name>.py`) handles threshold check + Slop emission. A view method (`Structure.<name>()` / `Lexicon.<name>()`) is the substrate's public API for the measurement. An algorithm helper (`slop/<substrate>/<name>.py`) holds the actual compute. Inline-vs-extract threshold: if the algorithm fits in roughly 30 LOC with no auxiliary helper functions, inline it on the view (`cyclomatic`, `cognitive`); otherwise extract to a `<name>.py` and have the view method delegate (`redundancy`, `hotspots`, `clones`). Module names are flat (no underscore prefix); private functions inside modules keep their leading underscore to mark intra-module privacy.
- **`cmd.py` convention.** Every CLI sub-package's root command lives in `<pkg>/cmd.py` (e.g. `slop/cli/cmd.py`, `slop/cli/install/cmd.py`).
- **`Result.json()` returns a dict; `Result.pretty()` returns a string.** Both delegate to `slop.linter.format`. The CLI does `json.dumps(result.json(), indent=2)` at the output boundary.
- **Config discovery walks upward** from CWD for `.slop.toml` or `pyproject.toml` with `[tool.slop]`. A pyproject without `[tool.slop]` is skipped, so sub-project pyproject files (like `src/pyproject.toml` in this repo) don't mask a repo-root `.slop.toml`.
- **Config schema is a versioned JSON asset, not a Python function.** `slop/config/schema/v1.json` is the committed source of truth; `slop schema [--version v1]` reads it via `importlib.resources`. A pytest drift guard (`tests/test_config_schema.py`) asserts the asset stays in sync with `Config` dataclass fields and `DEFAULT_RULE_CONFIGS` keys — adding a rule without updating the schema fails CI.
- **Exemptions are scope-keyed name lists (`ignore`), not waivers.** The old `[[waivers]]` array (id/path/rule/allow_up_to/expires + glob/fnmatch matching) was retired for a single membership check: a finding is suppressed when its `symbol` is in the ignore list for its `scope`. Global `[ignore]` (all rules) and per-rule `[rules.<rule>.ignore]` (carried in that rule's `params`), keyed by `functions`/`classes`/`modules`/`packages` (validated at load; unknown keys like `any` raise). The win over waivers is **scope precision** — `ignore.classes = ["Lexicon"]` waives the class-scope WMC without blinding `Lexicon`'s function-scope methods, which a path-level waiver fundamentally couldn't express. Suppression is silent (the exemption is auditable in config, not the output); there is no `allow_up_to` ceiling or `expires`. Matching lives in `dispatch.apply_ignores`.
- **Config-domain vs. rule-domain split.** `slop.config` owns config-file shape: `Config` (incl. the global scope-keyed `ignore` map), the TOML loader, the schema asset. `slop.linter.rule_config`, `slop.linter.severity`, `slop.linter.tags` stay in `linter/` — they're rule settings the config file *populates*, not config-file shape.
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
