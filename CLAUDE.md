# CLAUDE.md

## What this is

`slop` is an agentic code quality linter. It wraps metric kernels from `aux-skills` (PyPI) behind a unified linter interface with declarative config, threshold checking, and CI exit codes.

## Setup

```bash
# Full install (aux-skills backend + slop CLI, available system-wide)
./scripts/install.sh

# Development only (local venv, for running tests)
uv sync
```

The install script installs both `aux-skills` and `slop` as `uv tool` entries (available at `~/.local/bin/`). For local dev, `uv sync` sets up the project venv with `aux-skills` resolved from the sibling `../aux/cli` via `tool.uv.sources` in `pyproject.toml`.

## Common commands

```bash
# Run tests
uv run python -m pytest

# Run a single test file
uv run python -m pytest tests/test_engine.py

# Lint (against any codebase)
uv run slop lint --root /path/to/code

# List rules
uv run slop rules
```

## Project structure

```
src/slop/
  cli.py          CLI entry point (argparse)
  config.py       Config loading (.slop.toml / pyproject.toml / defaults)
  engine.py       Rule runner (iterate rules, collect results, compute exit code)
  output.py       Human-readable + JSON + quiet formatters
  models.py       Core dataclasses (Violation, RuleResult, LintResult, etc.)
  color.py        ANSI color helpers with TTY/NO_COLOR detection
  rules/
    __init__.py   Rule registry (RULE_REGISTRY, RULES_BY_NAME, etc.)
    complexity.py Wraps ccx_kernel + ck_kernel → cyclomatic, cognitive, weighted
    hotspots.py   Wraps hotspots_kernel → churn-weighted file hotspots
    architecture.py  Wraps robert_kernel → package design D'
    dependencies.py  Wraps deps_kernel → dependency cycles
    dead_code.py     Wraps prune_kernel → unreferenced symbols
    class_metrics.py Wraps ck_kernel → CBO, DIT, NOC
```

## Adding a new rule

1. Create `src/slop/rules/<name>.py` with a `run_<rule>(root, rule_config, slop_config) -> RuleResult` function
2. Add a `RuleDefinition` to `RULE_REGISTRY` in `rules/__init__.py`
3. Add default config in `config.py` `DEFAULT_RULE_CONFIGS`
4. Add to the generated config template in `config.py` `generate_default_config()`
5. Write tests in `tests/test_rules/test_<name>.py`

Rules are thin wrappers: load config params, call an aux kernel, iterate results, emit `Violation` objects for threshold breaches.

## Key design decisions

- **Kernels live in aux-skills, not slop.** slop imports `from aux.kernels.<x> import <x>_kernel`. No metric computation in slop.
- **Config priority:** `--config` flag > `.slop.toml` > `pyproject.toml [tool.slop]` > defaults.
- **14-day default hotspot window** — tuned for agentic code generation where architectural damage accumulates in days, not months.
- **Exit codes:** 0 = clean, 1 = violations, 2 = error.
