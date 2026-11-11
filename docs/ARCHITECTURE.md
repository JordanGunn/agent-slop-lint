# Architecture

slop is a linter on top of read-only primitives. Source: `src/slop/`.

## Layers

| Layer | Package / module | Role |
|---|---|---|
| AST | `ast/` | tree-sitter parse behind a `Node`/`AST` proxy; one `Grammar` class per language |
| Scope tree | `scope/` | `scan_corpus` carves the sources into a tree of components |
| Measures | `metrics/`, `lexicon/`, `graph/` | read-only views over a component |
| Vocabulary | `ontology/`, `lexical/` | canonical vocabulary (Open Ontology JSON IR) and the comparison with names in code |
| Lint | `rule.py`, `rules/`, `dispatch.py`, `violation.py`, `config.py` | rules compare a measure with a limit |
| CLI | `cli.py` | `ast`, `tree`, `find`, `lexicon`, `deps`, `vocab`, `shape`, `hotspots` (primitives); `lint`, `check`, `rules` (lint); `init`, `doctor` |

Primitive commands return facts and apply no limits. Only `rules/` and rule `limit` options
encode limits.

## Scope tree

`Corpus > Realm > Package > Module > Class > Callable` (`ScopeKind` in `scope/identity.py`).

- A `Realm` is one language; it owns that language's `Grammar`. Packages are directories.
- `Scope` (`scope/base.py`) is the shared interface: `id`, `name`, `qualname`, `extent`,
  `files`, `owner`, `children()`, `lexicon()`. `AggregateContainer` covers Corpus, Realm and
  Package; `SymbolContainer` covers Module, Class and Callable.
- `scope.scan_corpus(root, config)` (`scope/carve.py`) reads the files `scope/discover.py`
  lists, minus those matched by `exclude`. Inside a git work tree that list is tracked plus
  untracked-and-not-ignored files; elsewhere it is every file under the root except `.git`. Owners
  are set while the tree is built.
- Corpus-wide derived state (class hierarchy, module dependency graph) is built once at carve
  time and held in `AnalysisContext` (`scope/context.py`), reached through `component.context`.
- `Selection` (`scope/selection.py`) is a union of regions; `scope/find.py` implements
  `find`, `tree` and name collisions.

## Grammars

A `Grammar` (`ast/paradigm/base.py`) is tabular metadata plus extractor classmethods; it never
walks the tree. A language is one class in `ast/grammar/` (registered in
`GRAMMARS_BY_ID`: python, go, c, cpp, julia, java, csharp, rust, ruby, javascript,
typescript). It states:

- node types for callables, identifiers, and the decision, nesting, loop, switch, try and
  catch constructs used by complexity measures;
- operator and operand node types (Halstead), call nodes, language builtins;
- how names, parameters, class fields, imports and member access (`MemberAccess`) are read;
- implicit receiver names (`self`), constructor names, special methods.

Languages that share facts inherit them from a family parent instead of repeating them:
`ecmascript.py` (JavaScript, TypeScript) and `c_family.py` (C, C++). A fact that two grammars
spell the same way belongs in the parent; `duplicate-code` finds the ones that were missed.

Its `Paradigm` (`PROCEDURAL`, `OBJECT_ORIENTED`, `MULTI_PURPOSE`) selects the base class in
`ast/paradigm/`. Language-specific behaviour belongs in the grammar, not in `if lang` branches
elsewhere.

## How a rule runs

1. `cli.lint` loads `AnalysisConfig` (validated against `RULE_REGISTRY` in `rules/__init__.py`;
   unknown keys, unknown rules and options, and wrongly typed values are errors) and calls `scan_corpus`.
2. `Dispatcher.run` walks the tree once and indexes components by `ScopeKind`. For each
   enabled rule it calls `rule.check(component, rule_config)` at every component of each
   altitude in `rule.altitudes`.
3. A rule yields `Violation`s (`rule`, `path`, `line`, `column`, `message`, optional `value`
   and `threshold`). `Violation.at(scope, ...)` locates one at a scope's definition.
4. Violations on a line with `slop: ignore` (or `slop: ignore[a, b]`, exact rule names) are dropped, then the rest are sorted by path and position.
5. A rule that visited zero components is listed in `Report.zero_visited` rather than passing
   silently. Exit code: 0 no violations (warnings allowed), 1 any violation, 2 error.

Objective and subjective violations: a violation is objective when it follows from syntax and a
stated limit alone. A rule whose findings need judgement of idiom or intent (`class-cohesion`,
`rigid-package`, `useless-package`) sets `subjective = True`; the dispatcher then reports its
findings as warnings (`WARN` in the human output, `warnings` in JSON) that never fail the run.
A case that cannot be a rule at all (an integer literal, a short string) is not reported;
judging those and the warnings is the job of a layer that reads context. `magic-float` and
`duplicate-string` show the split: they measure a float operand and a repeated long string,
and say nothing about integers or short strings.

Contributor invariants:

- A rule subclasses `Rule` (`name`, `description`, `altitudes`, `default_config`, `check`);
  most subclass `Limit` (`rules/limit.py`), which names one altitude and a default limit and
  reads the `limit` option.
- A rule does not compute its measure and does not traverse beyond the component it is
  given. Measures live in `metrics/structural/` and are read through `Structure.over(component)`
  (`metrics/structural/view.py`), so `shape`, `find` and rules share one number.
- A new rule is added to `RULE_REGISTRY`; `slop rules` and `slop init` are generated from it.

## Inference

`slop/infer/` is a layer over the linter, imported only by `cli.py` and `slop/skill/` (pinned by
`tests/test_layers.py`). Slop never calls a model: the host agent does the inferring. This
package frames what the agent sees, fixes the shape of what it may return, and validates and
stores the result. It follows `Dpre(X) -> A(X' : Sigma) : S -> Dpost(Y)`.

| Subpackage | Role | May import |
|---|---|---|
| `bundle/` | prose slop ships and prints: `instructions.md`, `references/` (rubrics among them) | nothing in slop |
| `contract/` | the documents exchanged (`Worklist`, `Verdicts`, `Receipt`), their JSON Schema, strict parsing | nothing in slop |
| `ledger/` | persisted rulings (`Ledger`, `JsonlLedger`) | `contract` |
| `frame/` | finding id, code fingerprint, excerpt, the question and rubric for a rule | `bundle`, `contract` |
| `source/` | where residue comes from (`Source`, `FindingSource`) | `contract`, `frame` |
| `apply/` | validate verdicts, store them, list what is outstanding, settle a report | `contract`, `frame`, `ledger`, `source` |

`tests/test_infer_layers.py` pins these directions. A new kind of residue, such as a project
survey for bootstrapping, is a new module in `source/`; the other layers do not change.

The commands print or consume these documents, so an agent needs only the CLI:

| Command | Does |
|---|---|
| `slop infer instructions` | prints the agent's workflow |
| `slop infer references [NAME]` | lists the references, or prints one |
| `slop infer schema [NAME]` | prints the JSON Schema of every document, or of one |
| `slop infer next` | prints a `Worklist`: warnings of rules that have a rubric and no current ruling |
| `slop infer apply [FILE]` | validates a `Verdicts` document (file or stdin), stores what it accepts, prints a `Receipt` |

`slop lint` then settles the report with the ledger: a `clear` ruling drops the warning, a
`confirm` ruling makes it a violation (it fails the run), and a `defer` ruling, a stale ruling
or no ruling leaves it a warning. A ruling is stale when the excerpt's text or the rubric
changed, which `Ledger.current` checks through the fingerprint.

Only `class-cohesion` has a rubric. A field is declared once with `described(...)`; the schema
and the parser both read it. The ledger is `.slop/inferences.jsonl` under the project root, one ruling per line. The project
root is the directory holding the config (`.slop.toml` or `[tool.slop]`), else the scan root, so
a finding's id, its path and its ruling are the same whichever directory is scanned. Paths are
labelled by `frame/location.py`.

Constants: one used by a single module stays in it. One needed by a second module in the same
subpackage moves to that subpackage; the contract's closed terms are in `contract/vocabulary.py`.
One needed by a second package goes in `slop/layout.py` (`CONFIG_FILENAME`, `STATE_DIR`).

## Skills

`slop/skill/` packages Agent Skills (agentskills.io) that teach an agent to use slop, one per
job. It imports `infer`; nothing below it imports `skill`.

| Module | Role |
|---|---|
| `model.py` | `Skill`: name, description, manifest body, files; refuses what the spec forbids |
| `catalog.py` | `SKILLS`, every skill by name; one function per skill, its body in `manifests/<name>.md` |
| `install.py` | writes `DEST/<name>/` |

A skill's files are built from their single sources each time it is shown or installed:
`slop-infer` takes its instructions and rubrics from `infer/bundle/` and its schemas from
`infer/contract/`. Nothing is copied into the repository, so an installed skill cannot drift
from the source it was built from; reinstalling updates it.

`slop skill list` lists them, `slop skill show NAME [FILE]` prints the manifest or one file, and
`slop skill install NAME --dest DIR [--force]` writes the directory. A new skill is a new
function in `catalog.py` and a manifest in `manifests/`.
