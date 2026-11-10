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
(`vocab`). On top of them sits a plain **lint** layer: 12 rules, each a threshold on a
well-cited measure (McCabe, Campbell, Nejmeh, Martin, Chidamber & Kemerer), at limits
tuned for that pace. Judgement over what the checks find (which violations matter, what
to do about them) is a separate, later inference layer; it is not part of slop's lint.

## Example

```
$ slop lint --root .
src/app/config.py:12:1: complexity.cyclomatic app.config.load has cyclomatic complexity 14 (limit 10)
src/app/grid.py:40:1: structure.duplication 2 Type-2 clones (43 leaf nodes): src/app/grid.py:40 grid.a, src/app/grid.py:61 grid.b
Found 2 violations.
```

One `path:line:column: rule message` line per violation, then `Found N violations.` (or
`No violations.`). Exit `0` none, `1` any violation, `2` error (including a missing or
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
the lint layer. A dispatcher runs each rule at the scope it needs, and every violation
is reported at the narrowest scope it is about, with the line and column of that scope's
definition.

A rule is a threshold on a measure: it reports a violation when the measure is strictly
greater than its limit. A violation is a location, a rule name and one factual sentence
naming the unit and the number; nothing else is attached.

## Rules

12 rules, language-agnostic across 11 grammars. `slop rules` lists them with altitude and
enabled state. Each traces to a published source or a standard concept. Limits are the
defaults; a violation needs the measure to be strictly greater.

| Rule | Altitude | Default limit | Source |
|---|---|---|---|
| `complexity.cyclomatic` | callable | 10 | McCabe (1976) |
| `complexity.cognitive` | callable | 15 | Campbell (2018) |
| `complexity.combinatorial` | callable | 400 | NPath, Nejmeh (1988) |
| `structure.god-module` | module | 20 top-level definitions | module size boundary |
| `structure.rigidity` | package | D' 0.7 | Martin, Zone of Pain |
| `structure.uselessness` | package | D' 0.7 | Martin, Zone of Uselessness |
| `structure.dependency-cycles` | corpus | none (any cycle) | Acyclic Dependencies Principle |
| `structure.duplication` | corpus | 2 clones (`params.min_leaf_nodes` = 10) | Type-2 clones |
| `class.coupling` | class | CBO 8 | Chidamber & Kemerer (1994) |
| `class.inheritance-depth` | class | DIT 4 | Chidamber & Kemerer (1994) |
| `class.children` | class | NOC 10 | Chidamber & Kemerer (1994) |
| `class.cohesion` (off by default) | class | LCOM4 groups 1 | Hitz & Montazeri (1995) |

`class.cohesion` counts the groups of methods joined through shared instance members
(`self.x`, `this.x`) and lists them; a class with several groups may be several classes.
Constructors, static and class methods are left out, and methods that reach no instance
state are listed as detached, not as groups. Measured for Python, JavaScript and
TypeScript; Java, C# and C++ report `lcom4: null` because a bare `x` can mean `this.x`,
which syntax alone cannot resolve. `slop shape` prints every class's CK profile and
cohesion groups regardless of these rules.

Suppress a violation inline, on the line it is reported at (any comment syntax):
`# slop: ignore[complexity.cyclomatic]`. `slop: ignore` alone drops every rule on that
line; a family prefix (`slop: ignore[complexity]`) covers its rules.

## Languages

Eleven tree-sitter grammars: Python, JavaScript, TypeScript, Go, Java, C#, Rust, Julia, C,
C++, Ruby. Object-oriented metrics (the `class.*` rules, inheritance) apply where the language has
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
slop shape [--scope Q]             Each class's CK profile and cohesion groups (LCOM4), unfiltered

Lint (exit 0 no violations / 1 any violation / 2 on error)
slop lint --root <path>            Run all enabled rules
slop check <family|rule> --root    Run one namespace family or rule
slop rules                         List rules (name, altitude, enabled)

Housekeeping
slop schema                        Config schema as JSON (generated from the registry)
slop init --root <path>            Write a .slop.toml template
slop doctor                        Check that tree-sitter is available
slop --version                     Print the installed version
```

The primitives regenerate from the current source each run. `--scope` takes a qualname or
a file path; a package shares its qualname with its `__init__` module, so `tree` and
`lexicon` ask you to pick with `--scope-kind` instead of guessing. `find` matches the local
name exactly and reports `path:line` and language; `--collisions` lists names defined by more
than one scope of a kind (class by default) *within one language*, so a type mirrored once in
Python and once in TypeScript is not a collision.

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
"Declared names" are modules, packages, classes, their properties (class-body fields and
members assigned through `self`/`this`; Python, JavaScript and TypeScript), callables and
their parameters; builtin and library references (`self`, `np`, `int`), special methods,
implicit receivers and local variables are excluded by grammar facts, not by language
branches. There are no thresholds: the undefined list is ordered, not filtered.

`--output human` (default) or `--output json`. Run `slop --help` for the full list.

## Configuration

slop walks upward from `--root` for a `.slop.toml`, or a `pyproject.toml` with a
`[tool.slop]` table. Only three top-level keys are accepted; anything else (including the
removed `[ignore]` table) is a load error:

```toml
exclude = ["tests/**", "**/vendor/**"]   # files never carved; globs relative to the config's directory
languages = ["python", "typescript"]     # optional: carve only these languages (default: all supported)

[rules."complexity.cyclomatic"]
enabled = true                    # class.cohesion is the only rule off by default
thresholds.callable = 12          # keyed by the rule's declared altitude

[rules."structure.duplication"]
params.min_leaf_nodes = 20        # rule-specific noise floor
```

A rule table accepts only `enabled`, `thresholds` and `params`. `exclude` and `languages`
apply to every command. The read-only commands (`find`, `tree`, `lexicon`, `deps`,
`vocab`, `shape`) read only those two; `[rules]` matters to `lint` and `check` alone, so a
stale rule name there cannot block a question about the code.

A threshold keyed to an altitude the rule doesn't declare, or a param the rule doesn't
declare, is a load error, not a silent no-op, so "not flagged" is verifiably clean.
`slop schema` prints the exact shape and `slop init` writes a commented template. (The CLI
takes `--root` directly; the config's keys are not a scan path.) Details in
[docs/CONFIG.md](docs/CONFIG.md).

## Acknowledgments

slop implements metrics from McCabe, Chidamber & Kemerer, Nejmeh, Martin, Tornhill, and
Campbell — full bibliography in [NOTICE](NOTICE). AI-assistance and contributor credits in
[CITATIONS.md](CITATIONS.md). Changelog in [CHANGELOG.md](CHANGELOG.md).

## License

Apache 2.0. See [LICENSE](LICENSE).
