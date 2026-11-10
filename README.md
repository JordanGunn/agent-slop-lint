# slop

A linter and code-structure query tool. It parses source with tree-sitter into an ownership
tree (Corpus › Realm › Package › Module › Class › Callable). Read-only commands answer
questions about that tree with facts and no limits. The linter checks 12 published measures
against limits and prints `path:line:column: rule message`.

```
$ slop lint --root .
a.py:1:1: cyclomatic-complexity a.f has cyclomatic complexity 11 (limit 10)
a.py:1:1: npath-complexity a.f has NPath 1024 (limit 400)
Found 2 violations.
```

Exit `0` no violations, `1` any violation, `2` error.

## Install

Python 3.11+.

```bash
uv sync && uv run slop lint --root .     # from a checkout
uv tool install .                        # or install `slop` as a uv tool
```

`slop doctor` checks that tree-sitter is available.

## Commands

Read-only (exit `0` answered, `2` could not answer):

| Command | Answers |
|---|---|
| `slop ast <file>` | the parse tree of one file |
| `slop tree` | the ownership tree beneath a scope |
| `slop find <name>` / `--collisions` | where a name is defined; names defined more than once |
| `slop lexicon` | a scope's identifier vocabulary; with `--ontology IR.json`, its coverage by a canonical vocabulary |
| `slop deps` | the module dependency graph (`--cycles`) |
| `slop vocab --ontology IR.json` | class names compared with an [Open Ontology](https://open-ontology.com) JSON IR |
| `slop shape` | each class's CK profile and cohesion groups |
| `slop hotspots` | files changed in a revision window (`--since REV`, `--last N`, plus uncommitted changes), ranked by churn × complexity |

Lint:

| Command | Does |
|---|---|
| `slop lint` | run every enabled rule |
| `slop check RULE [RULE...]` | run only the named rules, even if disabled |
| `slop rules` | list rules, whether each is on, and its altitude |

Housekeeping: `slop init` writes a commented `.slop.toml` template; `slop doctor`.
`slop <command> --help` lists options (`--root`, `--output human|json`, ...).

## Rules

A rule reports a violation when its measure is strictly greater than `limit`.

| Rule | Altitude | Default limit | Source |
|---|---|---|---|
| `cyclomatic-complexity` | callable | 10 | McCabe (1976) |
| `cognitive-complexity` | callable | 15 | Campbell (2018) |
| `npath-complexity` | callable | 400 | Nejmeh (1988) |
| `god-module` | module | 20 top-level definitions | |
| `rigid-package` | package | D' 0.7 | Martin (1994, 2002) |
| `useless-package` | package | D' 0.7 | Martin (1994, 2002) |
| `import-cycle` | corpus | any cycle | Acyclic Dependencies Principle |
| `duplicate-code` | corpus | clone of 2+ callables (`min_leaf_nodes` 10) | Type-2 clones |
| `class-coupling` | class | CBO 8 | Chidamber & Kemerer (1994) |
| `class-inheritance-depth` | class | DIT 4 | Chidamber & Kemerer (1994) |
| `class-children` | class | NOC 10 | Chidamber & Kemerer (1994) |
| `class-cohesion` (off) | class | LCOM4 groups 1 | Hitz & Montazeri (1995) |

Suppress inline, on the reported line: `# slop: ignore[cyclomatic-complexity]`.

## Configuration

`.slop.toml` (or `[tool.slop]` in `pyproject.toml`), found by walking up from `--root`:

```toml
exclude = ["tests/**"]

[rules.cyclomatic-complexity]
limit = 12

[rules.class-cohesion]
enabled = true
```

Reference: [docs/CONFIG.md](docs/CONFIG.md).

## Languages

Python, JavaScript, TypeScript, Go, Java, C#, Rust, Julia, C, C++, Ruby. Class rules apply
where the language has classes; package and dependency rules where it has a module system.

## License

Apache 2.0, see [LICENSE](LICENSE). Measure attributions: [NOTICE](NOTICE).
