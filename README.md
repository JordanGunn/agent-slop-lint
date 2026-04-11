# slop

Agentic code quality linter — catches slop before it becomes architectural rot.

`slop` is a language-agnostic linter that detects structural quality defects across a codebase using established software metrics. It ships with opinionated defaults tuned for AI-assisted development, where code rot accumulates faster than in human-only workflows.

One CLI. One config file. Ten rules. Exit code 0 or 1.

## Installation

```bash
# Clone and run the install script (installs aux-skills backend + slop)
git clone https://github.com/JordanGunn/slop.git
cd slop
./scripts/install.sh
```

The install script checks system dependencies, installs `aux-skills` (the computational backend), installs `slop`, and verifies both are available in PATH.

**System requirements:** Python 3.10+, [uv](https://docs.astral.sh/uv/), `git`, `rg` ([ripgrep](https://github.com/BurntSushi/ripgrep)), `fd`/`fdfind` ([fd](https://github.com/sharkdp/fd)).

**Windows:** Use `.\scripts\install.ps1` instead.

## Quick start

```bash
# Run all rules with defaults
slop lint

# See what's available
slop rules

# Generate a config file to customize
slop init
```

## Rules

| Rule | Default | What it measures | Citation |
|---|---|---|---|
| `complexity.cyclomatic` | CCX > 10 | Per-function path count | McCabe 1976 |
| `complexity.cognitive` | CogC > 15 | Per-function reading difficulty | Campbell 2018 |
| `complexity.weighted` | WMC > 50 | Per-class aggregate method complexity | Chidamber & Kemerer 1994 |
| `hotspots` | 90d window | Files that are complex AND frequently changed | Tornhill 2015 |
| `packages` | D' > 0.7 | Package design distance from the Main Sequence | Martin 1994 |
| `deps` | any cycle | Dependency cycles between modules | — |
| `orphans` | disabled | Unreferenced symbols (advisory, needs human review) | — |
| `class.coupling` | CBO > 8 | Classes coupled to too many other classes | Chidamber & Kemerer 1994 |
| `class.inheritance.depth` | DIT > 4 | Inheritance hierarchies that are too deep | Chidamber & Kemerer 1994 |
| `class.inheritance.children` | NOC > 10 | Base classes with too many direct subclasses | Chidamber & Kemerer 1994 |

## Configuration

slop loads config from (in priority order):

1. `--config <path>` flag
2. `.slop.toml` in the project root
3. `pyproject.toml` `[tool.slop]` section
4. Built-in defaults

Generate a starter config:

```bash
slop init
```

### `.slop.toml`

```toml
root = "."
# languages = ["python", "typescript"]
# exclude = ["**/test_*", "**/vendor/**"]

[rules.complexity]
enabled = true
cyclomatic_threshold = 10
cognitive_threshold = 15
weighted_threshold = 50
severity = "error"

[rules.hotspots]
enabled = true
since = "90 days ago"
min_commits = 2
fail_on_quadrant = ["hotspot"]
severity = "error"

[rules.packages]
enabled = true
max_distance = 0.7
fail_on_zone = ["pain"]
severity = "warning"

[rules.deps]
enabled = true
fail_on_cycles = true
severity = "error"

[rules.orphans]
enabled = false
min_confidence = "high"
severity = "warning"

[rules.class]
enabled = true
coupling_threshold = 8
inheritance_depth_threshold = 4
inheritance_children_threshold = 10
severity = "error"
```

## CLI reference

```
slop lint                              Run all enabled rules
slop lint --root ./src                 Override root directory
slop lint --output json                JSON output (for agents/CI)
slop lint --output quiet               Summary only (one line)
slop lint --max-violations 0           Show all violations (no cap)
slop lint --no-color                   Disable ANSI colors

slop check complexity                  Run one category
slop check complexity.cyclomatic       Run one rule
slop check class.inheritance           Run a subcategory

slop init                              Generate .slop.toml
slop rules                             List rules with thresholds
slop schema                            Config schema as JSON
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | No violations |
| `1` | One or more violations found |
| `2` | Configuration or runtime error |

### Output modes

**human** (default) — grouped by category and sub-rule, top 5 violations per rule with `...and N more`, colored when connected to a terminal.

**json** — structured JSON with per-rule violations, summaries, and metadata. Designed for agent consumption and CI pipelines.

**quiet** — one-line summary: `53 violations | 2 advisories | FAIL`

## Language support

| Language | Extensions | Complexity | Hotspots | Packages | Deps | Class |
|---|---|---|---|---|---|---|
| Python | `.py` | yes | yes | yes | yes | yes |
| JavaScript | `.js`, `.mjs`, `.cjs` | yes | yes | — | yes | yes |
| TypeScript | `.ts`, `.tsx` | yes | yes | — | yes | yes |
| Go | `.go` | yes | yes | yes | yes | yes |
| Rust | `.rs` | yes | yes | — | — | yes |
| Java | `.java` | yes | yes | — | yes | yes |

`packages` (Martin metrics) currently supports Go and Python only. Other languages' files are excluded from the relevant rules, not errored.

## Why 90 days?

Tornhill's canonical hotspot window is 1 year, calibrated for human release cycles. slop defaults to 90 days because agentic code rot accumulates on a steeper curve — a 1-year window on an agent-assisted repo drowns the recent signal in human-era noise. Override with `--since` or the `rules.hotspots.since` config key.

## Architecture

slop is a thin orchestration layer. The computational backend is [aux-skills](https://github.com/JordanGunn/aux), which provides deterministic metric kernels built on tree-sitter, ripgrep, fd, and git. slop wraps those kernels with a linter interface: declarative config, threshold checking, human/JSON/quiet output, and CI exit codes.

No metric computation happens in slop itself. When aux-skills gains a new kernel, slop gains a new rule with zero kernel work.

## Acknowledgments

slop implements metrics from established software engineering research. Full citations are in [NOTICE](NOTICE).

| Metric | Author(s) | Year |
|---|---|---|
| Cyclomatic Complexity | Thomas J. McCabe | 1976 |
| Cognitive Complexity | G. Ann Campbell (SonarSource) | 2018 |
| CBO, DIT, NOC, WMC | Shyam R. Chidamber & Chris F. Kemerer | 1994 |
| Instability, Abstractness, D' | Robert C. Martin | 1994, 2002 |
| Hotspot analysis | Adam Tornhill | 2015 |
| Dependency cycle detection | Robert E. Tarjan | 1972 |

These are mathematical formulas computed from source code structure. slop implements them independently via tree-sitter AST traversal — no code from the original authors' implementations is used.

## License

Apache 2.0 — see [LICENSE](LICENSE)
