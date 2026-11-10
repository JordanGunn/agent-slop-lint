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
   silently. Exit code: 0 no violations, 1 any violation, 2 error.

Contributor invariants:

- A rule subclasses `Rule` (`name`, `description`, `altitudes`, `default_config`, `check`);
  most subclass `Limit` (`rules/limit.py`), which names one altitude and a default limit and
  reads the `limit` option.
- A rule does not compute its measure and does not traverse beyond the component it is
  given. Measures live in `metrics/structural/` and are read through `Structure.over(component)`
  (`metrics/structural/view.py`), so `shape`, `find` and rules share one number.
- A new rule is added to `RULE_REGISTRY`; `slop rules` and `slop init` are generated from it.
