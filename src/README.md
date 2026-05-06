# slop

A code quality linter for codebases where AI agents are writing most of the diffs.

[![PyPI](https://img.shields.io/pypi/v/agent-slop-lint)](https://pypi.org/project/agent-slop-lint/)
[![Python](https://img.shields.io/pypi/pyversions/agent-slop-lint)](https://pypi.org/project/agent-slop-lint/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

Static-analysis defaults were calibrated for codebases where a productive human wrote ~100 lines on a busy day and another human reviewed every one. An agent can drop that much into a single file before emitting its first status message, and the damage — deep coupling, WMC-heavy classes, duplicated handlers, files that grow 500 LOC in a week, identifier soup that bloats every downstream prompt — lands inside one session rather than over quarters. `slop` runs well-cited metrics across three substrates — structural (McCabe, Chidamber & Kemerer, Nejmeh, Martin, Tornhill, Campbell), information-theoretic (Halstead), and lexical (identifier vocabulary) — at thresholds tuned for that pace.

## Example

```
$ slop lint

slop 1.0.0 — scanning .

structural.complexity
  cyclomatic
    ✗ src/pipeline/ingest.py:44 process_batch — CCX 18 exceeds 10
    ✗ src/pipeline/ingest.py:112 _normalize_rows — CCX 14 exceeds 10
  cognitive
    ✗ src/pipeline/ingest.py:44 process_batch — CogC 26 exceeds 15
  3 violations, 142 checked

structural.hotspots (14 days ago, 87 commits)
  ✗ src/pipeline/transformation.py — CCX=45, growth +367 LOC
  ✗ src/lifecycle/tasks/write.py — CCX=41, growth +556 LOC
  2 violations

structural.duplication
  ⚠ . — clone density 7.2% exceeds threshold 5.0% (12 cloned functions across 4 clusters)
  ⚠ src/api/handlers/users.py:88 update_user — function 'update_user' is a Type-2 clone (fingerprint a3b1c4d2f001) — also at: src/api/handlers/orgs.py:74, src/api/handlers/teams.py:81
  2 violations

information.volume
  ✗ src/pipeline/ingest.py:44 process_batch — Volume 2147 exceeds 1500
  1 violation, 412 checked

information.magic_literals
  ⚠ src/billing/discount.py:31 apply_promo — 'apply_promo' contains 5 distinct magic numeric literals (threshold: 3): 7, 14, 30, 86400, 0.15
  1 violation

lexical.stutter
  ⚠ src/services/user_service.py:47 user_update_user_profile — identifier 'user_update_user_profile' repeats tokens ['user'] from enclosing class 'UserService'
  ⚠ src/services/user_service.py:91 get_user_user_id — identifier 'get_user_user_id' repeats tokens ['user'] from enclosing class 'UserService'
  2 violations, 412 checked

────────────────────────────────────────
6 violations | 5 advisories | 22 rules checked | FAIL
```

Exit `0` clean, `1` on violations, `2` on error. Works in CI, pre-commit, and interactively.

## Install

```bash
pip install agent-slop-lint
```

slop shells out to `rg`, `fd`, and `git`. Install via your system package manager (`apt install ripgrep fd-find git`, `brew install ripgrep fd git`, or equivalent) and run `slop doctor` to verify. Full per-platform steps, CI recipes, and pre-commit wiring are in the [setup guide](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/SETUP.md).

## Rules

slop ships 25 rules across three suites:

- **`structural.*`** — control-flow complexity, CK class metrics, hotspots, package distance, dependency cycles, duplication, god modules, type-discipline rules.
- **`information.*`** — Halstead volume and difficulty, magic literals, section-divider comments.
- **`lexical.*`** — identifier verbosity, tersity, and stutter against the enclosing scope.

The full rule index with default thresholds, citations, and per-rule pages lives in [`docs/rules/`](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/rules/README.md). For threshold tuning and the `default` / `lax` / `strict` profiles, see the [configuration reference](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/CONFIG.md).

## Languages

| Language | Complexity | Hotspots | Packages | Deps | Class |
|---|---|---|---|---|---|
| Python, JavaScript, TypeScript, Go, Java, C# | yes | yes | yes | yes | yes |
| Rust | yes | yes | yes | — | yes |
| Julia | yes | yes | yes | yes | — |
| C | yes | yes | yes (warn) | yes (best-effort) | — |
| C++ | yes | yes | yes | yes (best-effort) | yes |
| Ruby | yes | yes | yes (warn) | yes (best-effort) | yes |

Language-specific caveats (JavaScript packages, Rust deps, Julia CK metrics, C class metrics, C/C++ `-I`-path resolution and out-of-line method attribution, Ruby type-discipline rules silent-skip and open-class WMC aggregation) are documented in the [C notes](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/C.md), the [C++ notes](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/CPP.md), the [Julia notes](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/JULIA.md), the [Ruby notes](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/RUBY.md), and the relevant rule pages.

## CLI

```
slop lint                         Run all enabled rules
slop check <category|rule>        Run one category or rule
slop init [default|lax|strict]    Generate .slop.toml
slop doctor                       Check fd, rg, git are installed
slop hook                         Install a git pre-commit hook
slop skill <dir>                  Install the bundled agent skill
slop rules                        List rules with thresholds
slop schema                       Config schema as JSON
```

Output formats are `--output human` (default), `--output json` (CI and agents), and `--output quiet`. Run `slop --help` for the full flag list.

## Configuration

slop walks upward from CWD looking for `.slop.toml` first, then `pyproject.toml` with a `[tool.slop]` table — the same discovery ruff and mypy use. `root` resolves relative to the config file's directory. `--config` and `--root` on the CLI override both.

```bash
slop init          # balanced defaults
slop init lax      # legacy or gradual adoption
slop init strict   # greenfield or quality-focused
```

Every threshold, profile, and waiver mechanism is documented in the [configuration reference](https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/CONFIG.md).

## Architecture

slop ships its own discovery primitives and metric kernels. Each rule is a thin wrapper that loads config, calls a deterministic kernel, and emits `Violation` objects for threshold breaches. Primitives are organised by substrate — `_fs` (fd), `_text` (ripgrep), `_ast` (tree-sitter) — with cross-tool primitives in `_compose` and metric kernels in `_structural` and `_lexical`. One `pip install` gives you the whole thing; no companion runtime.

## Acknowledgments

slop implements metrics from McCabe, Halstead, Chidamber & Kemerer, Nejmeh, Martin, Lakos, Tornhill, and Campbell. Full bibliography in [NOTICE](NOTICE). AI assistance and contributor credits in the [project CITATIONS](https://github.com/JordanGunn/agent-slop-lint/blob/main/CITATIONS.md).

## License

Apache 2.0. See [LICENSE](LICENSE).
