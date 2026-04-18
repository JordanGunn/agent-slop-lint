# CLAUDE.md

## What this is

`slop` is an agentic code quality linter. It ships its own metric kernels under `src/cli/slop/_aux/` (tree-sitter, ripgrep, fd, git) and exposes them through a rule interface with declarative config, threshold checking, and CI exit codes. Self-contained — no external runtime dependency beyond the tree-sitter wheels already listed in `pyproject.toml`.

## Repo layout

```
slop/                       <- repo root (docs, LICENSE, NOTICE, README, .slop.toml, .github, scripts)
  src/
    pyproject.toml
    .gitignore              <- Python-specific (caches, venv, dist, uv.lock, ...)
    cli/
      slop/                 <- the Python package (import slop)
        cli.py              CLI entry point (argparse)
        config.py           Config loading (upward walk; .slop.toml / pyproject[tool.slop] / defaults)
        engine.py           Rule runner (iterate rules, collect results, compute exit code)
        output.py           Human / JSON / quiet formatters
        models.py           Core dataclasses (Violation, RuleResult, LintResult, ...)
        color.py            ANSI color helpers with TTY/NO_COLOR detection
        preflight.py        System-binary preflight (fd, rg, git)
        rules/              Thin wrappers around _aux kernels
        _aux/               Vendored metric kernels (excluded from slop's own lint and ruff)
    tests/
```

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

# Run tests
uv run python -m pytest

# Run a single test file
uv run python -m pytest tests/test_engine.py

# Lint (against any codebase)
uv run slop lint --root /path/to/code

# List rules
uv run slop rules
```

## Adding a new rule

1. Create `src/cli/slop/rules/<name>.py` with `run_<rule>(root, rule_config, slop_config) -> RuleResult`
2. Add a `RuleDefinition` to `RULE_REGISTRY` in `rules/__init__.py`
3. Add default config in `config.py` `DEFAULT_RULE_CONFIGS`
4. Add to the generated config template in `config.py` `generate_default_config()`
5. Write tests in `src/tests/test_rules/test_<name>.py`

Rules are thin wrappers: load config params, call a kernel under `slop._aux`, iterate results, emit `Violation` objects for threshold breaches.

## Key design decisions

- **Kernels live in `slop._aux`, not as an external dep.** slop imports `from slop._aux.kernels.<x> import <x>_kernel`. The vendored tree is Apache-2.0 licensed; see `src/cli/slop/_aux/LICENSE` and the repo-root `NOTICE` for attribution.
- **Config discovery walks upward** from CWD for `.slop.toml` or `pyproject.toml` with `[tool.slop]`. A pyproject without `[tool.slop]` is skipped, so sub-project pyproject files (like `src/pyproject.toml` in this repo) don't mask a repo-root `.slop.toml`.
- **14-day default hotspot window.** Tuned for agentic code generation where architectural damage accumulates in days, not months.
- **Exit codes:** 0 = clean, 1 = violations, 2 = error.

## README/LICENSE duplication

`README.md` and `LICENSE` are tracked in two places: the repo root (for GitHub's landing page) and `src/` (for PyPI, via hatchling). Hatchling validates the `readme` and `license-files` paths against the pyproject directory before applying force-include, so it will not accept `../README.md`-style paths. When updating either file, update both copies. If this drift becomes painful, add a pre-commit hook or CI check that fails when `src/README.md` and `README.md` (or the two `LICENSE` files) disagree.
