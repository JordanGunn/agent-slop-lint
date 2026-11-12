# Architecture

slop is a linter on top of read-only primitives. Source: `src/slop/`.

## Layers

| Layer | Package / module | Role |
|---|---|---|
| AST | `ast/` | tree-sitter parse behind a `Node`/`AST` proxy; one `Grammar` class per language |
| Scope tree | `scope/` | `scan_corpus` carves the sources into a tree of components |
| Measures | `metrics/`, `lexicon/`, `graph/` | read-only views over a component |
| Vocabulary | `ontology/`, `lexical/` | the project's vocabulary (SKOS terms) and the comparison with the words in code |
| Lint | `rule.py`, `rules/`, `dispatch.py`, `violation.py`, `config.py` | rules compare a measure with a limit |
| Agglomeration | `agglomeration.py` | groups the findings the code's structure relates (Oizumi et al. 2016); facts, never violations |
| CLI | `cli/` (one module per command family) | `ast`, `tree`, `find`, `lexicon`, `deps`, `shape`, `hotspots` (primitives); `ontology`; `lint`, `check`, `rules` (lint); `init`, `doctor` |

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
- name binding: a tree-sitter locals query per grammar (`ast/grammar/locals/<id>.scm`:
  `@local.scope`, `@local.definition.parameter|var|import|field|method`, `@local.reference`,
  `@ignore`) and two facts, `hoisted_bindings` and `class_scope_visible`; `ast/binding.py`
  resolves every name occurrence to a `SymbolKind` (parameter, local, import, field, method,
  free) with the tree-sitter-highlight algorithm. Fields defined in a class are its properties;
  clones rename only the parameters and locals a callable binds; LCOM4 reads members reached
  through the receiver (`MemberAccess`) and bare names bound to the class's own fields and methods,
  and leaves out accessors (`ast/accessor.py`: one statement returning or plainly assigning one
  member), which `Callable.kind` reports as `CallableKind.ACCESSOR`;
- how names, parameters, imports and explicit member access (`MemberAccess`) are read, and
  which corpus modules an import loads (`resolve_import`): a file-relative import (Python dots,
  `./` and `../`, quoted `#include`, `require_relative`, Rust `self`/`super`/`crate`) is
  anchored at the importing file and never matched by a bare name;
- implicit receiver names (`self`), constructor names, special methods.

Languages that share facts inherit them from a family parent instead of repeating them:
`ecmascript.py` (JavaScript, TypeScript) and `c_family.py` (C, C++). A fact that two grammars
spell the same way belongs in the parent; `duplicate-code` finds the ones that were missed.

Its `Paradigm` (`PROCEDURAL`, `OBJECT_ORIENTED`, `MULTI_PURPOSE`) selects the base class in
`ast/paradigm/`. Language-specific behaviour belongs in the grammar, not in `if lang` branches
elsewhere.

## How a rule runs

1. `cli.lint.lint` loads `AnalysisConfig` (validated against `RULE_REGISTRY` in `rules/__init__.py`;
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

- A rule subclasses `Rule` (`name`, `description`, `altitudes`, `default_options`, `check`);
  most subclass `Limit` (`rules/limit.py`), which names one altitude and a default limit and
  reads the `limit` option.
- A rule does not compute its measure and does not traverse beyond the component it is
  given. Measures live in `metrics/structural/` and are read through `Structure.over(component)`
  (`metrics/structural/view.py`), so `shape`, `find` and rules share one number.
- A new rule is added to `RULE_REGISTRY`; `slop rules` and `slop init` are generated from it.

## Inference

`slop/infer/` is a layer over the linter, imported only by `cli/` and `slop/skill/` (pinned by
`tests/test_layers.py`). Slop never calls a model: the host agent does the inferring. This
package frames what the agent sees, fixes the shape of what it may return, and validates and
stores the result. It follows `Dpre(X) -> A(X' : Sigma) : S -> Dpost(Y)`.

| Subpackage | Role | May import |
|---|---|---|
| `bundle/` | prose slop ships and prints: `instructions.md`, `references/` (rubrics among them) | nothing in slop |
| `contract/` | the documents exchanged (`Residue`, `Verdicts`, `Receipt`), their JSON Schema, strict parsing | nothing in slop |
| `ledger/` | persisted rulings (`Ledger`, `JsonlLedger`) | `contract` |
| `frame/` | finding id, project-relative location, code fingerprint, the question and rubric for a rule | `bundle`, `contract` |
| `source/` | where residue comes from (`Source`, `FindingSource`) | `contract`, `frame` |
| `apply/` | validate verdicts, store them, settle a report | `contract`, `frame`, `ledger`, `source` |

`tests/test_infer_layers.py` pins these directions. A new kind of residue, such as a project
survey for bootstrapping, is a new module in `source/`; the other layers do not change.

The agent works from the linter's own output. `slop lint --output json` attaches a `residue`
to each warning and to each agglomeration: the id, the `locations`
to read (the whole lines of the subject's extent, so a class shows its definition and a package
every module in it; for a group, the lead's extent and then each unit's), the closed question, the rubric command and version, the fingerprint, and the ruling's `status`
(`none`, `stale`, `defer` or `confirm`). The output also states `root`, the absolute scan root
that finding paths are relative to, and `project_root`, the absolute root that residue paths are
relative to, so the agent can open the code from any working directory. Every finding has an
`id` (rule, project-relative path, subject, and for `duplicate-string` and `magic-float` the
literal), its `scope` and its `related` scopes. `agglomerations` lists the groups the findings
form: an `id`, a `topology` (`intra-method`, `intra-class`, `hierarchical`, `intra-component`,
`cross-component`), the `lead` scope, the `units` and the member finding ids. A group never
changes the exit code. The agent reads the code
at that span and the rubric, then sends verdicts. `slop infer` keeps only what nothing else does:

| Command | Does |
|---|---|
| `slop infer apply [FILE]` | validates a `Verdicts` document (file or stdin) against the current findings, stores what it accepts, prints a `Receipt` |
| `slop infer references [NAME]` | lists the references (the rubrics), or prints one |
| `slop infer schema [NAME]` | prints the JSON Schema of `residue`, `verdicts` and `receipt`, or of one |
| `slop infer instructions` | prints the agent's workflow |

`slop lint` settles the report with the ledger (`apply/settle.py`): a `clear` ruling drops the
finding, a `confirm` ruling makes it a violation (it fails the run), and a `defer` ruling, a
stale ruling or no ruling leaves it a warning. A ruling is stale when the definition's text or
the rubric changed since it was given, which the fingerprint records. A new ruling for the same
id replaces the old one, so a confirmed finding can be ruled on again.

Every subjective rule ships a rubric, and so does `agglomeration`; a test pins that, because a
warning without one could never be ruled on and would stay a warning forever. A rubric is one
bundled file, `references/rubrics/<rule>.md`, that states its closed question on a
`Question:` line and the criteria for each outcome; the question's id is the rule. A confirmed agglomeration is
recorded and shown but never fails the run. A field is declared once with `described(...)`; the schema
and the parser both read it. The ledger is `.slop/inferences.jsonl` under the project root, one ruling per line. The project
root is the directory holding the config (`.slop.toml` or `[tool.slop]`), else the scan root, so
a finding's id, its path and its ruling are the same whichever directory is scanned.
`frame/location.py` turns an extent's byte spans into the lines a residue shows and fingerprints.

Constants: one used by a single module stays in it. One needed by a second module in the same
subpackage moves to that subpackage; the contract's closed terms are in `contract/vocabulary.py`.
One needed by a second package goes in `slop/layout.py` (`CONFIG_FILENAME`, `STATE_DIR`).

## Vocabulary

The lexicon says which words the code uses; the ontology says what words mean in the project's
domain, whether or not the code uses them. `slop/ontology/` holds the project's vocabulary as
W3C SKOS terms in `<project root>/.slop/ontology.json`, beside the inference ledger, committed:
each term is one word (`prefLabel`) with its `definition`, other accepted words (`altLabel`),
retired or misspelt words (`hiddenLabel`), and `broader` and `related` terms. A term binds the
code only once it has a definition; an undefined term is a draft candidate.

| module | role |
|---|---|
| `model.py` | `Term`, `Scheme` (lookup by any label, `preferred`, `narrower`) |
| `fs.py` | strict reading and writing of the file |
| `check.py` | integrity: single-word labels, SKOS S13, S14 extended to the scheme (one word, one term), S27, links and `broader` cycles |
| `draft.py` | seeds the vocabulary from the words the code declares, keeping what is agreed |
| `occurrence.py` | where a word reaches the code, and the edits a rename would make (declarations and references, case preserved) |

The vocabulary flows down without lower layers importing it: `lexicon.Vocabulary` is a protocol
(`preferred(word)`), the lint command loads the file and passes it to `scan_corpus`, and the
`preferred-term` rule reads it from the analysis context. `lexical/` compares the code's declared
words with the defined terms (`slop lexicon`).

## Skills

`slop/skill/` packages Agent Skills (agentskills.io). Slop ships one, `slop` (`/slop`): the
single point of agentic access. The agent reads the user's ask, finds the matching capability,
takes the exact options from `slop --help` and `slop COMMAND --help`, runs the commands and
answers in prose. Its capabilities table is checked against the parser, so a new command fails
the tests until the table names it. It imports `infer`; nothing below it imports `skill`.

| Module | Role |
|---|---|
| `model.py` | `Skill`: name, description, manifest body, files; refuses what the spec forbids |
| `catalog.py` | `SKILLS`, every skill by name; one function per skill, its body in `manifests/<name>.md` |
| `install.py` | writes `DEST/<name>/`, replaces only a recorded earlier install |

A skill's files are built from their single sources each time it is shown or installed:
`slop` takes the inference workflow and rubrics from `infer/bundle/` and the schemas from
`infer/contract/`. Nothing is copied into the repository. An installed skill is a snapshot of
the slop that wrote it, and goes stale when slop is upgraded until it is reinstalled.

`install` builds the whole tree before touching disk and records what it wrote in
`.slop-skill.json` (the skill, the slop version, the files). `--force` replaces only a
directory with that record for the same skill: it overwrites the skill's files, removes files
the earlier install wrote that the skill no longer has, and leaves anything else in place.

`slop skill list` lists them, `slop skill show NAME [FILE]` prints the manifest or one file, and
`slop skill install NAME --dest DIR [--force]` writes the directory.
