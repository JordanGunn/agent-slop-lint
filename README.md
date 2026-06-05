# slop

A code-quality linter for codebases where AI agents write most of the diffs.

[![PyPI](https://img.shields.io/pypi/v/agent-slop-lint)](https://pypi.org/project/agent-slop-lint/)
[![Python](https://img.shields.io/pypi/pyversions/agent-slop-lint)](https://pypi.org/project/agent-slop-lint/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

> **Status: v3 (`3.0.0a0`) is a ground-up rebuild on a component model and is pre-release.**
> `pip install` still serves the released 1.x line; install v3 from source (below).

Static-analysis defaults were calibrated for a world where a productive human wrote ~100
lines on a busy day and another human reviewed every one. An agent can drop that much into
one file before its first status message — and the damage (deep coupling, god classes,
duplicated handlers, files that grow 500 LOC in a week, identifier soup that bloats every
downstream prompt) lands inside one session, not over quarters. `slop` runs well-cited
metrics — structural (McCabe, Chidamber & Kemerer, Nejmeh, Martin, Tornhill, Campbell) and
lexical (identifier vocabulary) — at thresholds tuned for that pace, and is built to be
read by the agent: every finding is either a **directive** it can act on or **evidence** it
should investigate.

## Example

```
$ slop lint --root .

VERDICTS
  [error] complexity.cognitive  ·  doctor.run_doctor
      cognitive complexity 20 exceeds threshold 15
      → reduce-complexity: Flatten doctor.run_doctor: lift nested conditionals into guard
        clauses or extract the deepest branch into a named helper (cognitive 20 > 15).
  [warning] lexical.stutter  ·  config.load_config
      'load_config' restates its module 'config'
      → drop-redundant-tokens: drop the tokens the name shares with its scope.

OBSERVATIONS
  [info] lexical.cohesion  ·  grep
      module 'grep' shares only 0% of its vocabulary with the rest of package 'text' —
      a possible foreign body. Consider whether it belongs here.

0 verdict(s) ... — exit 1
```

Exit `0` clean, `1` on any error-severity verdict, `2` on error (including a missing or
source-free `--root`). Works in CI, pre-commit, and interactively; `--output json` for
agents and pipelines.

## Install

v3 is pre-release — install from source as a `uv` tool:

```bash
./scripts/install.sh          # installs `slop` system-wide via uv tool + checks deps
# or, for development:
uv sync                       # dev env in .venv (includes pytest, ruff)
uv run slop lint --root .
```

slop shells out to `rg`, `fd`, and `git` for discovery and the churn signal. Install them
with your package manager (`apt install ripgrep fd-find git`, `brew install ripgrep fd git`)
and run `slop doctor` to verify.

## How it works

A parse of the sources is carved once into an ownership tree —
**Corpus › Realm › Package › Module › Class › Callable** — and two read-only views project
over any scope: `Structure` (control flow, coupling, duplication) and `Lexical` (naming and
vocabulary). A dispatcher runs each rule at the scope it needs, and every finding attributes
to the *narrowest scope it is about*, with a line where one applies.

Findings come in three strengths, matched to how confidently slop can speak:

- **Verdict** — a defect with a prescribed fix (`reduce-complexity`, `extract-helper`,
  `break-dependency-cycle`). Error-severity verdicts fail the build.
- **REVIEW** — slop is confident the structure is anomalous but the remedy is a judgment it
  won't make for you (warning-capped, never fails the build).
- **Observation** — a claim-free, evidence-backed nudge where no fix is honestly
  prescribable (e.g. the identifier distribution, a foreign-body module). It makes no
  precision claim, so it can't be a false positive.

## Rules

25 rules, language-agnostic across 11 grammars. `slop rules` lists them with altitude and
disposition.

- **Complexity** (per callable, error): `complexity.cyclomatic` (McCabe), `complexity.cognitive`
  (Campbell), `complexity.combinatorial` (NPath, Nejmeh).
- **Structure**: `structure.duplication` (Type-2 clones), `structure.dependency-cycles`
  (Acyclic Dependencies Principle, error), `structure.god-module`, `structure.call-islands`,
  `structure.redundancy`, `structure.runts`, `structure.rigidity` / `structure.uselessness`
  (Martin's distance-from-main-sequence), `structure.escape-hatches`,
  `structure.hidden-mutators`, `structure.sentinels`.
- **Class**: `class-shape` — the Chidamber–Kemerer suite (CBO/DIT/NOC/WMC) as an observation.
- **Lexical**: `lexical.stutter` (a name restating its scope), `lexical.verbosity`,
  `lexical.sprawl` (a closed alphabet acting as an undeclared type), `lexical.imposters`
  (a parameter that is really a receiver — a class in hiding), `lexical.slackers` (a real
  cluster whose names don't align), `lexical.hammers` (institutionalised catch-all
  vocabulary), `lexical.cohesion` (a module foreign to its package).
- **Whole-corpus signals** (observations): `vocabulary` (identifier token distribution),
  `hotspots` (churn × complexity, Tornhill), `orphans` (unreferenced top-level symbols).

`imposters`/`slackers` are observations on their own; they promote to a REVIEW verdict only
when an independent structural signal (clones or redundant siblings) corroborates them.

## Languages

Eleven tree-sitter grammars: Python, JavaScript, TypeScript, Go, Java, C#, Rust, Julia, C,
C++, Ruby. Object-oriented metrics (class-shape, inheritance) apply where the language has
classes; package/dependency metrics where it has a module system.

## CLI

```
slop lint --root <path>           Run all enabled rules
slop check <family|rule> --root   Run one namespace family or rule
slop rules                        List rules (name, disposition, altitude)
slop schema                       Config schema as JSON (generated from the registry)
slop init --root <path>           Write a .slop.toml template
slop doctor                       Check tree-sitter / git availability
slop ast <file>                   Print a file's parse tree (named skeleton; --raw, --max-depth)
slop lexicon [--scope Q]          Print a scope's vocabulary distribution (Zipf/hapax + head)
slop deps [--scope Q] [--cycles]  Print the module dependency graph (resolved/unresolved edges)
slop --version                    Print the installed version
```

The view commands (`ast`, `lexicon`, `deps`) are read-only structural inspectors —
sub-file-resolution skeletons, regenerated from the current source each run. `--scope`
takes a qualname or a file path; `--output json` emits the machine form.

`--output human` (default) or `--output json`. Run `slop --help` for the full list.

## Configuration

slop walks upward from `--root` for a `.slop.toml`, or a `pyproject.toml` with a
`[tool.slop]` table. Two sections:

```toml
[rules."complexity.cyclomatic"]
enabled = true
thresholds.callable = 12          # keyed by the rule's declared altitude

[ignore]
classes = ["LegacyAdapter"]       # scope-keyed exemptions: functions/classes/modules/packages
```

A threshold keyed to an altitude the rule doesn't declare is a load error, not a silent
no-op — so "not flagged" is verifiably clean. `slop schema` prints the exact shape. (The CLI
takes `--root` directly; the config's keys are rule settings, not a scan path.)

## Acknowledgments

slop implements metrics from McCabe, Chidamber & Kemerer, Nejmeh, Martin, Tornhill, and
Campbell — full bibliography in [NOTICE](NOTICE). AI-assistance and contributor credits in
[CITATIONS.md](CITATIONS.md). Changelog in [CHANGELOG.md](CHANGELOG.md).

## License

Apache 2.0. See [LICENSE](LICENSE).
