# slop

A code quality linter for codebases where AI agents are writing most of the diffs.

[![PyPI](https://img.shields.io/pypi/v/agent-slop-lint)](https://pypi.org/project/agent-slop-lint/)
[![Python](https://img.shields.io/pypi/pyversions/agent-slop-lint)](https://pypi.org/project/agent-slop-lint/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

Static analysis tools got their defaults from codebases where a productive human wrote maybe 100 lines on a busy day and another human reviewed every one. An agent can drop that much into a single file before emitting its first status message, and the structural damage (deep coupling, WMC-heavy classes, files that grow 500 LOC in a week) lands inside one session rather than accumulating over quarters. The usual review cadence does not catch it. `slop` is calibrated for that pace.

The metrics themselves are not new. Cyclomatic complexity (McCabe 1976), the CK suite for classes (Chidamber and Kemerer 1994), package distance from the Main Sequence (Martin 1994), churn-weighted hotspots (Tornhill 2015): all well-cited, all mostly ignored in day-to-day workflows because they were tuned for human timescales. slop wraps them behind one CLI with thresholds that assume a different pace of change.

## Example

```
$ slop lint

slop 0.6.1 — scanning .

complexity
  cyclomatic
    ✗ src/pipeline/ingest.py:44 process_batch — CCX 18 exceeds 10
    ✗ src/pipeline/ingest.py:112 _normalize_rows — CCX 14 exceeds 10
    ✗ src/store/frame.py:204 append_partition — CCX 11 exceeds 10

  cognitive
    ✗ src/pipeline/ingest.py:44 process_batch — CogC 26 exceeds 15
    ✗ src/store/frame.py:204 append_partition — CogC 21 exceeds 15

  6 violations, 142 checked

hotspots (14 days ago)
  ✗ src/lifecycle/tasks/write.py — CCX=41, growth +556 LOC
  ✗ src/pipeline/transformation.py — CCX=45, growth +367 LOC
  2 violations

packages
  ⚠ src/config — Zone of Pain (I=0.12, A=0.00)
  ⚠ src/core/distributed/dag — Zone of Pain (I=0.18, A=0.05)
  ⚠ src/core/transform — Zone of Pain (I=0.09, A=0.03)
  3 advisories

deps
  ✓ clean, 55 checked

class
  coupling
    ✗ tests/v2/test_pdrf_types.py:12 PdrfTestSuite — CBO 11 exceeds 8

  1 violation, 8 checked

orphans (disabled)
  ℹ skipped (enable in .slop.toml)

────────────────────────────────────────
9 violations | 3 advisories | 8 rules checked | FAIL
```

Exit code is `0` when clean, `1` on violations, `2` on configuration or runtime error. Works in CI, pre-commit hooks, and interactively.

## Install

```bash
pip install agent-slop-lint
```

slop shells out to `rg`, `fd`, and `git`. Install those via your system package manager (`apt install ripgrep fd-find git`, `brew install ripgrep fd git`, or equivalent) and run `slop doctor` to verify.

Full per-platform install steps, CI recipes, pre-commit wiring, and the agent skill are in the [setup guide](./docs/SETUP.md).

## Rules

| Rule | Default | Measures | Source |
|---|---|---|---|
| `complexity.cyclomatic` | CCX > 10 | Per-function path count | McCabe 1976 |
| `complexity.cognitive` | CogC > 15 | Per-function reading difficulty | Campbell 2018 |
| `complexity.weighted` | WMC > 40 | Per-class aggregate method complexity | Chidamber and Kemerer 1994 |
| `halstead.volume` | V > 1500 | Per-function information content (Length × log2 Vocabulary) | Halstead 1977 |
| `halstead.difficulty` | D > 30 | Per-function operator/operand density | Halstead 1977 |
| `npath` | NPath > 400 | Per-function acyclic execution path count | Nejmeh 1988 |
| `hotspots` | 14-day window | Files that are complex AND growing fast | Tornhill 2015 |
| `packages` | D' > 0.7 | Package design distance from the Main Sequence | Martin 1994 |
| `deps` | any cycle | Dependency cycles between modules | Lakos 1996, Martin 2002 |
| `orphans` | disabled | Unreferenced symbols (advisory) | — |
| `class.coupling` | CBO > 8 | Classes coupled to too many other classes | Chidamber and Kemerer 1994 |
| `class.inheritance.depth` | DIT > 4 | Inheritance hierarchies that are too deep | Chidamber and Kemerer 1994 |
| `class.inheritance.children` | NOC > 10 | Base classes with too many direct subclasses | Chidamber and Kemerer 1994 |

Per-threshold explanations, when to raise them, and the `default` / `lax` / `strict` profiles live in the [configuration reference](./docs/CONFIG.md).

### Why a 14-day hotspot window

Tornhill's original work used a 1-year window, tuned for release cycles where a file you had not touched in 9 months was stable and a file you had been touching for 9 months was probably structurally important. Agent workflows collapse that timescale. A file can go from 200 LOC to 800 LOC in a week, and the architectural decisions compounding inside that growth are the ones worth catching early rather than a year later when the file is already unrecoverable. The 14-day default rewards recency. Widen `rules.hotspots.since` to `"90 days ago"` for human-pace repos.

## Language support

| Language | Extensions | Complexity | Hotspots | Packages | Deps | Class |
|---|---|---|---|---|---|---|
| Python | `.py` | yes | yes | yes | yes | yes |
| JavaScript | `.js`, `.mjs`, `.cjs` | yes | yes | yes | yes | yes |
| TypeScript | `.ts`, `.tsx` | yes | yes | yes | yes | yes |
| Go | `.go` | yes | yes | yes | yes | yes |
| Rust | `.rs` | yes | yes | yes | — | yes |
| Java | `.java` | yes | yes | yes | yes | yes |
| C# | `.cs` | yes | yes | yes | yes | yes |

JavaScript has no `interface` or `abstract class` in the language itself, so every declared class is counted as concrete. A JavaScript package with `Ca > 0` and no abstraction will legitimately land in Martin's Zone of Pain; treat `packages` as an advisory signal rather than a gate on JavaScript code (it is `severity = "warning"` by default for that reason). Rust's `deps` rule is not implemented (no import graph yet); `packages` on Rust uses the trait/struct/enum split for abstractness and reports Ca=Ce=0 per package, so it mostly surfaces intra-crate abstraction balance rather than cross-crate coupling.

## Configuration

slop walks upward from the current directory looking for `.slop.toml` first and then `pyproject.toml` with a `[tool.slop]` table, the same discovery ruff and mypy use. When a config is discovered, its `root` key resolves relative to the config file's directory, so `root = "src"` in `~/project/.slop.toml` always points at `~/project/src` regardless of which subdirectory you invoked slop from. `--config` and `--root` on the CLI override both.

Generate a starter config:

```bash
slop init          # balanced defaults
slop init lax      # legacy or gradual adoption
slop init strict   # greenfield or quality-focused
```

Every threshold, the intent behind it, and the three profiles in full are documented in the [configuration reference](./docs/CONFIG.md).

## CLI

```
slop lint                         Run all enabled rules (default command)
slop check <category|rule>        Run one category or rule
slop init [profile]               Generate .slop.toml
slop doctor                       Check fd, rg, git are installed
slop hook                         Install a git pre-commit hook
slop skill <dir>                  Install the bundled agent skill
slop rules                        List rules with thresholds
slop schema                       Config schema as JSON
```

Run `slop --help` for the full flag list, or `slop <command> --help` for per-command options. Output formats are `--output human` (default), `--output json` for CI and agent consumption, and `--output quiet` for one-line summaries.

## Architecture

`slop` ships the metric kernels it needs directly. Each rule wraps a deterministic kernel built on tree-sitter AST traversal, ripgrep, fd, and git. The kernels live under `src/cli/slop/_aux/` in the repo and ride along in the installed wheel, so `pip install agent-slop-lint` gives you a single self-contained package with no companion runtime to install.

Rules are thin wrappers around those kernels: load config params, call the kernel, iterate results, emit `Violation` objects for threshold breaches. Adding a new metric is a new kernel plus a new rule file in `src/cli/slop/rules/`.

## Acknowledgments

slop implements metrics from established software engineering research. Full citations are in [NOTICE](NOTICE).

| Metric | Author(s) | Year |
|---|---|---|
| Cyclomatic Complexity | Thomas J. McCabe | 1976 |
| Cognitive Complexity | G. Ann Campbell (SonarSource) | 2018 |
| Halstead Volume, Difficulty | Maurice H. Halstead | 1977 |
| NPath | Brian A. Nejmeh | 1988 |
| CBO, DIT, NOC, WMC | Shyam R. Chidamber and Chris F. Kemerer | 1994 |
| Instability, Abstractness, D' | Robert C. Martin | 1994, 2002 |
| Acyclic Dependencies Principle | John Lakos; Robert C. Martin | 1996, 2002 |
| Hotspot analysis | Adam Tornhill | 2015 |
| Dependency cycle detection | Robert E. Tarjan | 1972 |

These are mathematical formulas computed from source code structure. slop implements them independently via tree-sitter AST traversal. No code from the original authors' implementations is used.

## Further reading

- [Configuration reference](./docs/CONFIG.md) — per-rule threshold guidance, the `default` / `lax` / `strict` profiles, when to tune or disable each rule.
- [Setup guide](./docs/SETUP.md) — per-platform install, CI recipes, pre-commit wiring, agent skill installation.
- [Design philosophy](./docs/philosophy/) — why these metrics, why external, what problem slop is solving.
- [References](./docs/philosophy/references.md) — full bibliography tied to each rule.
- [Changelog](./CHANGELOG.md)

## License

Apache 2.0. See [LICENSE](LICENSE).
