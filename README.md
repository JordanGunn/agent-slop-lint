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
downstream prompt) lands inside one session, not over quarters.

slop is built from the bottom up. The foundation is a set of read-only **primitives** an
agent can query for facts: a language-agnostic parse (tree-sitter), an ownership tree,
discovery over that tree (`find`, `tree`), identifier statistics (`lexicon`), the import
graph (`deps`), and a comparison of the names in code against a canonical vocabulary
(`vocab`). On top of them sits a **lint** layer of well-cited metrics — McCabe, Campbell,
Nejmeh, Martin, Chidamber & Kemerer, Tornhill, and Zipf for identifier distribution — at
thresholds tuned for that pace. Every finding is either a **directive** the agent can act
on or **evidence** it should investigate.

## Example

```
$ slop lint --root .

VERDICTS
  [error] structure.dependency-cycles  ·  python
      import cycle across 2 modules: config → settings → config
      → break-dependency-cycle: invert one dependency (depend on an abstraction, DIP),
        extract the shared code into a module both can depend on, or merge the modules
        if they are truly one concern.
  [warning] structure.duplication  ·  app  src/cli/app.py
      2 Type-2 clones: app.grid_group, app.surface_group
      → extract-helper-function: Extract a shared helper: 2 functions are Type-2 clones
        (structurally identical bodies, 43 leaf nodes).

OBSERVATIONS
  [info] vocabulary  ·  src/laszy/project/scan
      src/laszy/project/scan: Identifier vocabulary: 94 distinct tokens across 399 uses.
      Reuse follows a healthy Zipfian gradient (α=0.93, R²=0.92), typical of engineered
      code. …

40 verdict(s) (2 error, 38 warning), 27 observation(s) — exit 1
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
**Corpus › Realm › Package › Module › Class › Callable** — keyed by stable logical
identities. The primitives read that tree (`find`, `tree`, `lexicon`, `deps`, `vocab`);
the `Structure` view projects control flow, coupling and duplication over any scope for
the lint layer. A dispatcher runs each rule at the scope it needs, and every finding
attributes to the *narrowest scope it is about*, with a line where one applies.

Findings come in three strengths, matched to how confidently slop can speak:

- **Verdict** — a defect with a prescribed fix (`reduce-complexity`, `extract-helper`,
  `break-dependency-cycle`). Error-severity verdicts fail the build.
- **REVIEW** — slop is confident the structure is anomalous but the remedy is a judgment it
  won't make for you (warning-capped, never fails the build).
- **Observation** — a claim-free, evidence-backed nudge where no fix is honestly
  prescribable (e.g. the identifier distribution, a foreign-body module). It makes no
  precision claim, so it can't be a false positive.

## Rules

12 rules, language-agnostic across 11 grammars. `slop rules` lists them with altitude and
disposition. Each traces to a published source or a standard concept.

- **Complexity** (per callable, error): `complexity.cyclomatic` (McCabe), `complexity.cognitive`
  (Campbell), `complexity.combinatorial` (NPath, Nejmeh).
- **Structure**: `structure.duplication` (Type-2 clones), `structure.dependency-cycles`
  (Acyclic Dependencies Principle, error), `structure.god-module`, and
  `structure.rigidity` / `structure.uselessness` (Martin's distance-from-main-sequence).
- **Class**: `class-shape` — the Chidamber–Kemerer suite (CBO/DIT/NOC and method count) as an observation.
- **Whole-corpus signals** (observations): `vocabulary` (identifier token distribution, a
  Zipf near-invariant), `hotspots` (churn × complexity, Tornhill), `orphans` (unreferenced
  top-level symbols).

## Languages

Eleven tree-sitter grammars: Python, JavaScript, TypeScript, Go, Java, C#, Rust, Julia, C,
C++, Ruby. Object-oriented metrics (class-shape, inheritance) apply where the language has
classes; package/dependency metrics where it has a module system.

## CLI

```
Primitives (read-only facts; exit 0 when the question was answered, 2 when it could not be)
slop ast <file>                    Print a file's parse tree (named skeleton; --raw, --max-depth)
slop tree [--scope Q]              Print the ownership tree beneath a scope (--depth, --kind, --scope-kind)
slop find <name> | --collisions    Where a name is defined; or which names are defined more than once
slop lexicon [--scope Q] [--ontology IR.json]   Vocabulary distribution (Zipf/hapax + head); with an ontology, coverage of declared names
slop deps [--scope Q] [--cycles]   Print the module dependency graph (resolved/unresolved edges)
slop vocab --ontology IR.json      Compare class names with a canonical vocabulary (--term NAME: one entry)

Lint layer (exit 0 clean / 1 on any ERROR finding / 2 on error)
slop lint --root <path>            Run all enabled rules
slop check <family|rule> --root    Run one namespace family or rule
slop rules                         List rules (name, disposition, altitude)

Housekeeping
slop schema                        Config schema as JSON (generated from the registry)
slop init --root <path>            Write a .slop.toml template
slop doctor                        Check tree-sitter / git availability
slop --version                     Print the installed version
```

The primitives regenerate from the current source each run. `--scope` takes a qualname or
a file path; a package shares its qualname with its `__init__` module, so `tree` and
`lexicon` ask you to pick with `--scope-kind` instead of guessing. `find` matches the local
name exactly and reports `path:line`; `--collisions` lists names defined by more than one
scope of a kind (class by default).

Class questions discover each grammar's class-like definitions: classes, interfaces,
structs, enums and traits as the language has them. That includes C `struct`/`union`/`enum`
definitions (a specifier counts only with a body, and `typedef struct {...} Name;` is named
`Name`) and Julia `struct`, `abstract type` and parametric types. Answers carry a `caveats`
list (JSON) or `note:` lines (human) when they may be incomplete: files with syntax errors
are still carved but may have lost definitions. A known gap: TypeScript type aliases are
not discovered.

`vocab` reads the JSON IR that [Open Ontology](https://open-ontology.com) emits
(`pnpm model:check <model> --json`; the bare IR and that command's wrapper are both
accepted) and compares classes with the ontology's entities as matched, unknown, and
unused. Matching is exact after case and separator folding (`escalate-ticket` equals
`EscalateTicket`); a near miss such as `TicketManager` is reported as unknown, never
accepted. Only the declared schema is read, not facts seeded at runtime.

`lexicon --ontology IR.json` compares the *words* the code declares with the words the
ontology defines (term names and field keys; descriptions are prose and are not tokenised).
It reports the share of declared-name occurrences the ontology covers, the declared tokens
it does not define (most used first, with their file spread), the canonical tokens the
code never uses, and the canonical tokens the noise list strips before measurement
(`key`, `index`, `by` ...), which can never be observed and so are not called unused.
"Declared names" are modules, packages, classes, callables and their parameters; builtin
and library references (`self`, `np`, `int`), special methods and implicit receivers are
excluded by grammar facts, not by language branches. There are no thresholds: the
undefined list is ordered, not filtered.

`--output human` (default) or `--output json`. Run `slop --help` for the full list.

## Configuration

slop walks upward from `--root` for a `.slop.toml`, or a `pyproject.toml` with a
`[tool.slop]` table. Three keys:

```toml
exclude = ["tests/**", "**/vendor/**"]   # files never carved; globs relative to the config's directory

[rules."complexity.cyclomatic"]
enabled = true
thresholds.callable = 12          # keyed by the rule's declared altitude

[ignore]
classes = ["LegacyAdapter"]       # scope-keyed exemptions: functions/classes/modules/packages
```

`exclude` applies to every command. The read-only commands (`find`, `tree`, `lexicon`,
`deps`, `vocab`) read only `exclude`; `[rules]` and `[ignore]` matter to `lint` and `check`
alone, so a stale rule name there cannot block a question about the code.

A threshold keyed to an altitude the rule doesn't declare is a load error, not a silent
no-op — so "not flagged" is verifiably clean. `slop schema` prints the exact shape. (The CLI
takes `--root` directly; the config's keys are not a scan path.)

## Acknowledgments

slop implements metrics from McCabe, Chidamber & Kemerer, Nejmeh, Martin, Tornhill, and
Campbell — full bibliography in [NOTICE](NOTICE). AI-assistance and contributor credits in
[CITATIONS.md](CITATIONS.md). Changelog in [CHANGELOG.md](CHANGELOG.md).

## License

Apache 2.0. See [LICENSE](LICENSE).
