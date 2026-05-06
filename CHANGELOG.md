# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-05-06

The composition suite + lexical expansion release. Two new rule
suites address agent-written-code patterns that the v1.0.x lexical
rules couldn't reach: hidden-class candidates buried in flat function
families, and naming smells too narrow for the unified
`lexical.stutter`. Both suites are grounded in three rounds of
empirical PoC research (recorded under
`docs/observations/composition/`) and published prior art (Wille
1982; Caprile & Tonella 2000; Bavota et al.; Lawrie et al.;
Deissenboeck & Pizka; Harris 1955).

### Added

- **`composition.*` (new suite, 2 rules).**
  - `composition.affix_polymorphism` — Formal-Concept-Analysis-based
    detection of missing namespaces / inheritance hierarchies from
    affix-polymorphism patterns. Surfaces the inheritance lattice
    when one entity's operations strictly contain another's.
  - `composition.first_parameter_drift` — clusters of free functions
    sharing a first-parameter name; flags strong / weak / false-
    positive candidates. Strong clusters signal a missing receiver
    / hidden class.
  - Both default to `severity = "warning"` — these rules surface
    candidates, not violations of an objective threshold.
- **`lexical.*` expansion (6 new rules).**
  - `lexical.name_verbosity` — function/class names with too many
    word-tokens (class-without-class signal). Independent from
    `lexical.verbosity` (which measures *body* identifiers).
  - `lexical.numbered_variants` — identifiers ending in
    disambiguator suffixes (`_1`, `_v2`, `_old`, `_new`, `_local`).
  - `lexical.weasel_words` — configurable banlist for catchall
    vocabulary (`Manager`, `Helper`, `Util`, `Spec`, `Object`, …)
    with per-word position config (prefix/suffix/any/module_name)
    and per-word severity overrides.
  - `lexical.type_tag_suffixes` — identifier suffixes restating the
    type annotation (`result_dict: dict[...]`, `config_path: Path`).
  - `lexical.boilerplate_docstrings` — docstrings whose first-
    sentence content is a subset of function-name tokens.
  - `lexical.identifier_singletons` — functions where most named
    locals are write-once-read-once (default `severity = "info"`).
- **Methodology + citations docs.** New
  `docs/philosophy/composition-and-lexical.md` documents the
  empirical grounding and prior-art chain for the new suites.
  `docs/philosophy/references.md` extended with FCA, identifier-
  quality, and Extract-Class refactoring citations.
- **Shared function-definition enumerator** at
  `_lexical/_naming.py` (cross-language tree-sitter walk used by
  both composition rules and the new lexical rules).

### Changed

- **`lexical.stutter` split into three rules** so each smell can be
  configured independently:
  - `lexical.stutter.namespaces` — symbol stutters with module path.
  - `lexical.stutter.callers` — method/attribute stutters with
    enclosing class.
  - `lexical.stutter.identifiers` — local variable stutters with
    enclosing function (default `severity = "info"`).
- **Stutter token comparison is now case-insensitive.** The original
  unified rule missed cross-case stutters
  (`UserService` ↔ `user_service_helper`). Now matches correctly.

### Compatibility

- Legacy rule name `lexical.stutter` translates automatically to
  `lexical.stutter.identifiers` via `slop._compat`. The closest
  single-rule successor, chosen because it's what the original rule
  fired on most often in practice.
- Legacy TOML table `[rules.lexical.stutter]` migrates its keys to
  `[rules.lexical.stutter.identifiers]` at config-load time.
- Existing waivers referencing `lexical.stutter` keep working
  (translated through the same shim).
- A consolidated deprecation notice prints to stderr at config-load
  time; the canonical names appear in `docs/rules/`.

## [1.0.3] - 2026-05-05

Ruby language support across the full applicable rule set, **including
the CK class-metrics suite with open-class aggregation**. Same shape
of hotfix as v1.0.1 (C) and v1.0.2 (C++): `tree-sitter-ruby` was a
wheel dependency and `.rb` was registered in the AST extension map,
but no kernel `_LANG_CONFIG` registered `"ruby"`. Final of the three
planned single-language hotfixes.

### Added

- **Ruby language support** across structural, information, and
  lexical rule families. `structural.complexity.{cyclomatic,cognitive,
  npath}`, `information.{volume,difficulty,magic_literals,
  section_comments}`, `structural.{god_module,duplication,redundancy,
  hotspots,orphans,deps,packages,local_imports}`,
  `structural.types.sentinels`, `lexical.{stutter,verbosity,tersity}`,
  **and** `structural.class.{complexity,coupling,inheritance.depth,
  inheritance.children}` all run on Ruby files. See `docs/RUBY.md`.
- New `_ruby_*` helpers in `_structural/{ccx,npath,halstead}.py`.
  Method name extraction handles regular methods (`def foo`),
  singleton/class methods (`def self.foo`), operator overloads
  (`def ==`, `def []`, `def []=`, `def <=>`), and treats lambdas
  (`->{ }`), do-blocks (`do |x| end`), and curly blocks (`{ |x| }`)
  as anonymous (`<lambda>`).
- New `_extract_ruby_superclasses` and `_collect_ruby_classes` in the
  CK kernel. Ruby's class name is positional (a `constant` direct
  child) rather than a field, so it has its own collector path.
- New `_aggregate_ruby_open_classes` post-WMC pass. Ruby's open-class
  semantics let the same `class Foo` be re-declared across files;
  each declaration parses as a separate `class` node. The aggregator
  merges them by name within the Ruby subset, summing WMC and method
  counts, taking max CBO/DIT/NOC, and unioning superclasses. See
  `docs/RUBY.md` "Open-class aggregation".
- New `IMPORT_NODE_PREDICATES` hook on `_structural/local_imports.py`.
  Ruby's imports are method calls (`require 'foo'`), not statement
  nodes; the predicate distinguishes require-style calls from
  ordinary calls. Other languages don't register and pass through
  unchanged.
- `structural.packages` for Ruby treats `module` as the abstract
  analog (modules cannot be instantiated, only mixed in via
  `include`/`extend`). Classes are concrete. Ruby has no `final`.
  Default `severity = "warning"`.
- `structural.deps` for Ruby resolves `require_relative './foo'` to
  peer files; `require 'gem'` is treated as external.

### Structurally N/A — silent no-op

- **`structural.types.escape_hatches`** (any-type density). Ruby is
  dynamically typed; every parameter is implicitly `Object`. There
  is no type system to escape. Silent no-op via missing kernel
  registration; documented in `_structural/any_type_density.py`.
- **`structural.types.hidden_mutators`** (out-parameters). Ruby's
  parameter passing is always by reference; every object is mutable.
  Without a type system the rule has no signal-to-noise floor.
  Silent no-op via missing kernel registration; documented in
  `_structural/out_parameters.py`.

Both match the C-CK and Julia-CK silent-no-op posture established in
v1.0.1.

### Mixin posture (intentional, documented)

Ruby mixins (`include MyMod` / `extend MyMod`) count toward CBO
(captured as type references inside the class body) but NOT toward
DIT (Ruby community convention treats them as composition). NOC is
unaffected. See `docs/RUBY.md` "Mixin coupling" for the rationale
and the per-rule param hook for projects that want different
semantics.

### Behaviour change

Users upgrading from v1.0.2 with `.rb` files in their codebase will
see new violations across the full applicable rule set. By design —
those files were silently passing v1.0.2.

### Out of scope (logged, deferred)

Same pre-existing audit gaps carried forward from v1.0.1 / v1.0.2:
Java's npath `switch_node` mismatch; `lexical.stutter`'s missing
Java/C#/Julia entries; type-discipline message wording for non-Python
languages.

Ruby-specific deferrals:
- Mixin-aware DIT (could become a per-rule `include_mixins=true` param).
- `define_method` and metaprogramming visibility.
- `$LOAD_PATH` / Bundler / `RUBYLIB` resolution for `structural.deps`.
- Class methods inside `structural.redundancy` (free-method only).

## [1.0.2] - 2026-05-05

C++ language support across the full applicable rule set, **including
the CK class-metrics suite** (CBO, DIT, NOC, WMC). Same shape of
hotfix as v1.0.1 was for C: `tree-sitter-cpp` was a wheel dependency
and `.cpp` / `.cc` / `.cxx` were registered in the AST extension map,
but no kernel `_LANG_CONFIG` registered `"cpp"` — every metric kernel
silently skipped C++ files.

### Added

- **C++ language support** across structural, information, and
  lexical rule families. `structural.complexity.{cyclomatic,cognitive,
  npath}`, `information.{volume,difficulty,magic_literals,
  section_comments}`, `structural.{god_module,duplication,redundancy,
  hotspots,orphans,deps,packages,local_imports}`, `structural.types.
  {escape_hatches,hidden_mutators,sentinels}`, `lexical.{stutter,
  verbosity,tersity}`, **and** `structural.class.{complexity,coupling,
  inheritance.depth,inheritance.children}` all run on C++ files. See
  `docs/CPP.md` for the full status sheet.
- New `_cpp_*` helpers in `_structural/{ccx,npath,halstead}.py`
  paralleling the v1.0.1 `_c_*` helpers but extended to handle every
  C++ name shape: in-class methods (`field_identifier`), out-of-line
  methods (`qualified_identifier`), operator overloads
  (`operator_name`), destructors (`destructor_name`), pointer/
  reference-return wrappers, and lambda expressions
  (`lambda_expression` → named `<lambda>`).
- New `_extract_cpp_superclasses` callable on `_CkLangConfig["cpp"]`
  that walks `base_class_clause` children for `type_identifier` /
  `qualified_identifier` to support single + multiple inheritance.
- New `_collect_cpp_outofline_methods` second-pass walker in the CK
  kernel. C++ codebases conventionally declare classes in headers
  and define methods in `.cpp` files (`void Foo::bar() {}`); these
  out-of-line definitions parse as top-level `function_definition`s
  outside the class body. The walker catalogues them, and the WMC
  computation attributes each one's CCX back to the matching class
  by name.
- New `definition_unwrap_types: frozenset[str]` field on
  `_LangConfig` / `_NpathLangConfig` / `_HalsteadLangConfig`. Lets
  the kernel descend through wrapper node types (C++
  `template_declaration` is the canonical example) to find the
  wrapped `function_definition` / `class_specifier`. Default empty
  preserves existing behaviour for every other language.
- `_split_cpp_classes_by_abstract` in `_structural/robert.py`. A
  C++ class is **abstract** iff it has at least one pure-virtual
  method (`virtual T f() = 0;`) AND is not declared `final`.
  Drives the `structural.packages` abstractness term. Default
  `severity = "warning"`.
- `.hpp` and `.hxx` registered in `EXT_LANGUAGE_MAP` for C++.
  `.h` continues to default to C (conservative; codebases that use
  `.h` for C++ headers can override with explicit globs).

### Fixed

- **`structural.class.*` rules now cleanly silent-no-op when the
  user-requested language set excludes every CK-supported
  language.** The v1.0.1 fix to "no supported languages" returned
  an empty result without an error; v1.0.2 keeps that behaviour.

### Behaviour change

Users upgrading from v1.0.1 with C++ files in their codebase will
see new violations across the full rule set. By design — those
files were silently passing v1.0.1.

### Out of scope (logged, deferred)

- Java's npath `switch_node = "switch_statement"` mismatch with the
  grammar's `switch_expression` emission (still an unfixed
  pre-existing bug discovered during v1.0.1).
- `lexical.stutter`'s missing Java/C#/Julia entries in
  `_SCOPE_NODES` (still an unfixed pre-existing audit gap).
- C++20 / C++23 features that older `tree-sitter-cpp` versions
  don't emit (concepts, modules, coroutines).
- C++ class methods inside `structural.redundancy` (free-function
  only).
- Bare-name namespace collisions in WMC out-of-line attribution
  (documented in `docs/CPP.md`).
- Cross-translation-unit method definitions whose declaring header
  is outside the scanned set.

## [1.0.1] - 2026-05-05

C language support across the applicable rule set. Discovered during a
coverage audit that `tree-sitter-c` was a wheel dependency and `.c` /
`.h` were registered in the AST extension map but no kernel
`_LANG_CONFIG` registered `"c"` — same shape of silent-skip failure
that v0.7.0 had with Julia short-form functions. Hotfix.

### Added

- **C language support** (`.c`, `.h`) across structural, information,
  and lexical rule families. `structural.complexity.{cyclomatic,
  cognitive,npath}`, `information.{volume,difficulty,magic_literals,
  section_comments}`, `structural.{god_module,duplication,redundancy,
  hotspots,orphans,deps,packages,local_imports}`, `structural.types.
  {escape_hatches,hidden_mutators,sentinels}`, and `lexical.{stutter,
  verbosity,tersity}` all run on C files. The CK class metric family
  (`structural.class.*`) silently no-ops on `.c` / `.h` files (C has
  no class concept; same posture as Julia for CK). New `tree-sitter-c
  >= 0.21.0` was already a dependency; v1.0.1 wires it into the
  kernels. See `docs/C.md` for the full status sheet, including the
  documented limitations (no `-I` path resolution, A=0 always for
  packages, three-pattern out-parameter mutation detection).
- New `_c_find_function_identifier` and `_c_name_extractor` helpers
  on the `_LangConfig` Callable seam in `_structural/ccx.py`,
  `_structural/npath.py`, and `_structural/halstead.py`. Same shape
  as the Julia precedent — tree-sitter-c does not expose function
  names through a `name` field; the name lives in
  `function_declarator.declarator (identifier)`, optionally wrapped
  in `pointer_declarator` for pointer return types. Smaller kernels
  (`magic_literals`, `section_comments`, lexical) inline the
  declarator-chain walk in their generic `_fn_name` helpers.
- New `switch_body_types: frozenset[str]` field on the npath
  `_NpathLangConfig` dataclass. Lets the kernel descend through
  body-wrapper node types between a switch and its cases — required
  for C (`compound_statement`), Java (`switch_block` /
  `switch_block_statement_group`), and C# (`switch_body`). Default
  empty-frozenset preserves existing behaviour for Python/JS/TS/Go/
  Rust which expose cases as direct switch children.

### Fixed

- **`structural.complexity.npath` under-counted switches in C, C#, and
  Java**. Pre-1.0.1 the kernel iterated direct switch children
  looking for case nodes, but C wraps cases in `compound_statement`,
  C# in `switch_body`, and Java in `switch_block` /
  `switch_block_statement_group`. Cases were therefore invisible and
  every switch contributed `npath = 1`. v1.0.1 walks through the
  language's `switch_body_types` to find cases. Java's case shape
  remains constrained by a separate pre-existing issue
  (`switch_node = "switch_statement"` does not match tree-sitter-
  java's actual `switch_expression` emission for classic switches);
  that's tracked for a follow-up.
- **`structural.class.*` rules now silently no-op on languages that
  don't register CK metrics**, instead of returning a "No supported
  languages" error. Previously, running CK on a Julia or C codebase
  produced a per-rule error that polluted output and could fail CI.
  v1.0.1 returns a clean empty result when the user explicitly
  requested languages that this rule does not apply to.
- **`structural.deps` module-resolution index now includes
  extension-preserving keys**. C `#include "foo.h"` resolves to
  `foo.h` (not `foo`, which strips the suffix). The same change also
  picks up other languages that include extensions in their import
  strings; existing Python/JS/TS/Go/Java/C# tests are unaffected.

### Changed

- `structural.types.escape_hatches` (any-type density) regex pattern
  for C: escape hatch is `void *`; annotation pattern is calibrated
  tentatively. Default `severity = "warning"`. See `docs/C.md`.
- Section-comment divider regex widened to also match C block-style
  dividers (`/* === ... ===` and `/* --- ... ---`) alongside the
  existing `#`-style and `//`-style markers.

### Behaviour change to be aware of

Users upgrading from v1.0.0 with C files in their codebase may see
new violations across complexity, npath, halstead, packages, deps,
god_module, duplication, redundancy, magic_literals,
section_comments, types.{escape_hatches,hidden_mutators,sentinels},
local_imports, and lexical.* rules. This is by design — C files were
silently passing every rule in v1.0.0. To suppress the new output
gradually, set `severity = "warning"` per rule or disable
specific rules while you triage.

C, C# and Java codebases that have switch statements will see NPath
counts increase to reflect the actual case count. Tighten thresholds
if you previously calibrated against the under-counted numbers.

### Discoveries (out of scope; logged for follow-up)

- Java's `structural.complexity.npath` `switch_node = "switch_statement"`
  does not match tree-sitter-java's `switch_expression` node type for
  classic switch syntax. The v1.0.1 `switch_body_types` fix only
  helps on the wrapper-descent side; Java still needs a switch-node
  type fix.
- `lexical.stutter` is missing per-language entries for Java, C#, and
  Julia in `_SCOPE_NODES` — same shape of silent-skip failure C had
  pre-1.0.1.
- `structural.types.sentinels` advisory message text references
  Python remedies ("Literal[...] or Enum") even when reporting C
  violations. Wording will be language-aware in a follow-up.

## [1.0.0] - 2026-05-04

First stable release. The 0.9.0 → 1.0.0 jump is mostly additive: a new
`lexical.*` suite, type-discipline and shape rules under `structural.*`,
inline-density rules under `information.*`, and prefix-table semantics
for bulk-disabling rules in config. Rule names and the public CLI are
unchanged from 0.9.0.

### Added

- **`lexical.*` suite (3 rules).** A new measurement substrate covering
  identifier vocabulary discipline.
  - `lexical.stutter` — flags identifiers that repeat tokens from the
    enclosing scope (function, class, module). Catches names like
    `parse_parser_input` inside class `Parser`.
  - `lexical.verbosity` — flags functions where the mean identifier word
    count exceeds a threshold (default 3.0). Catches `compute_total_aggregated_user_score_value`-style drift.
  - `lexical.tersity` — flags functions where more than 50% of identifiers
    are ≤ 2 characters. Catches `p`/`q`/`x`-heavy code.
- **New structural rules (6).**
  - `structural.duplication` — Type-2 clone detection: structurally
    identical function bodies across the codebase.
  - `structural.god_module` — flags files with > 20 top-level callable
    definitions.
  - `structural.local_imports` — flags `import` statements inside function
    bodies. Three Python idiomatic patterns (optional heavy deps, CLI
    deferred imports, test monkeypatch imports) ship as commented-out
    waiver templates in `slop init`.
  - `structural.redundancy` — flags sibling top-level functions that share
    ≥ 3 non-trivial callees (refactoring signal for shared helper
    extraction).
  - `structural.types.sentinels` — flags `str`-annotated parameters with
    sentinel-shaped names (`status`, `mode`, `kind`, ...) where an enum
    would be more honest.
  - `structural.types.hidden_mutators` — flags functions that mutate
    collection-typed parameters in place.
  - `structural.types.escape_hatches` — flags files where the fraction of
    type annotations using `Any`, `interface{}`, `unknown`, etc. exceeds
    30%.
- **New information rules (2).**
  - `information.magic_literals` — flags functions with > 3 distinct
    non-trivial numeric literals.
  - `information.section_comments` — flags function bodies containing
    section-divider comments (a function-overload signal).
- **Prefix-table config semantics.** TOML tables `[rules.<prefix>]`
  propagate `enabled` and `severity` to every descendant rule. More
  specific tables override broader ones. Disabling an entire suite is now
  one line:
  ```toml
  [rules.lexical]
  enabled = false
  ```
  See `docs/CONFIG.md` "Disabling rules, groups, and suites".
- **`CITATIONS.md`** — credits the AI assistance (Augment Code's auggie
  Prism dynamic routing across Claude Opus 4.7, Claude Sonnet 4.5, and
  Gemini 2.5 Pro) and points to NOTICE for academic citations.

### Changed

- README trimmed substantially. The full rule index moved to
  `docs/rules/README.md` (where it was already authoritative).
  Long-form caveats moved to the rule pages and `docs/JULIA.md`.
- `docs/dogfood-deps-kernel.md` removed (case-study churn, no longer
  current).
- Rule wrappers `run_any_type_density` and `run_clone_density` now use
  named module-level constants instead of hard-coded magic numbers.
- `_lexical/stutter.py` `_scan_file` refactored for cognitive complexity
  (CogC 17 → 9).

### Fixed

- `_structural/sibling_calls.py` — corrected a logical error (`or` → `and`)
  in the shared-callee predicate that was producing inflated redundancy
  counts.

### Compatibility

- All 0.9.0 rule names and TOML tables continue to work unchanged.
- The legacy-name compatibility shim from 0.9.0 remains in place and is
  still scheduled for removal in 1.1.0.

## [0.9.0] - 2026-05-04

### Changed — rule taxonomy migration

- **All rule names now carry a suite prefix** matching `docs/rules/README.md`.
  This is a breaking change for anything that consumes the JSON `rule` field
  (CI parsers, dashboards, downstream tooling). Legacy names and TOML tables
  still work via a compatibility shim and trigger a single consolidated
  deprecation warning to stderr at config-load time. The shim is scheduled
  for removal in 1.1.0.
- Canonical rule names:
  - `complexity.cyclomatic` → `structural.complexity.cyclomatic`
  - `complexity.cognitive` → `structural.complexity.cognitive`
  - `complexity.weighted` → `structural.class.complexity`
  - `npath` → `structural.complexity.npath`
  - `hotspots` → `structural.hotspots`
  - `packages` → `structural.packages`
  - `deps` → `structural.deps`
  - `orphans` → `structural.orphans`
  - `class.coupling` → `structural.class.coupling`
  - `class.inheritance.depth` → `structural.class.inheritance.depth`
  - `class.inheritance.children` → `structural.class.inheritance.children`
  - `halstead.volume` → `information.volume`
  - `halstead.difficulty` → `information.difficulty`
- TOML config tables move under suite-prefixed paths
  (`[rules.structural.complexity]`, `[rules.information.volume]`,
  ...). The Halstead `volume_threshold` / `difficulty_threshold` keys are
  renamed to `threshold` under their respective new tables. The CK
  `weighted_threshold` key moves from `[rules.complexity]` to
  `[rules.structural.class.complexity]` as `threshold`.
- `slop check <name>` accepts both legacy and canonical names.
- `slop init` now emits canonical TOML.
- All bundled documentation and the agent skill ship with canonical names.

### Compatibility shim

- `slop._compat` is the single point of translation. Legacy → canonical
  maps for rule names, category names, and TOML tables all live there.
- Waivers using legacy rule names are translated at load time and listed
  in the deprecation block.

## [0.7.1] - 2026-04-26

**Released to PyPI** on 2026-04-26 as `agent-slop-lint==0.7.1`. Tag: [`v0.7.1`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.7.1).

### Refactored

- **Per-language name extraction and function-node matching now live as Callable fields on each kernel's `_LangConfig`**, matching the established `extract_superclasses: SuperclassExtractor` pattern in `class_metrics`. Each of `_structural/ccx.py`, `_structural/npath.py`, and `_structural/halstead.py` gains `name_extractor: NameExtractor` and `is_function_node: FunctionNodeMatcher` fields with sensible defaults that reproduce v0.7.0 behaviour for every existing language. Removes the language-branching `if node.type == "function_definition":` block that v0.7.0 introduced into shared kernel functions. No behaviour change for Python / JavaScript / TypeScript / Go / Rust / Java / C#.

### Fixed

- **Short-form Julia function definitions** (`f(x) = x + 1`) are now detected and analysed by `complexity.cyclomatic`, `complexity.cognitive`, `complexity.npath`, `halstead.volume`, and `halstead.difficulty`. v0.7.0 silently skipped these because tree-sitter parses them as `assignment` nodes with a `call_expression` LHS rather than `function_definition`. Variable assignments (`x = 1`, `y = some_func()`) are correctly excluded.
- **Operator-method definitions** (`+(a, b) = ...`, `-(a::Int, b::Int) = ...`) are now detected and named by their operator symbol (e.g. `+`, `-`).
- **Do-blocks** (`map(xs) do x ... end`) are now treated as anonymous functions named `<lambda>`, with their decisions counted independently from the enclosing call.
- **Method extensions on dotted names** (`function Base.show(...)` → name `show`) — previously returned `<anonymous>` in violation output.
- **Where-clause function signatures** (`function f(x) where T ... end` → name `f`) — previously returned `<anonymous>` because the call_expression was nested inside a `where_expression` the v0.7.0 walker did not descend into.

### Behaviour change to be aware of

Users upgrading from v0.7.0 to v0.7.1 on Julia codebases that contain
short-form functions, do-blocks, operator methods, or dotted method
extensions may see new complexity / npath / halstead violations on
code that previously passed silently. This is by design — those
functions were not being analysed at all in v0.7.0.

## [0.7.0] - 2026-04-26

**Released to PyPI** on 2026-04-26 as `agent-slop-lint==0.7.0`. Tag: [`v0.7.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.7.0).

### Added

- **Julia language support** (`.jl`) across the structural rule family. `complexity.cyclomatic`, `complexity.cognitive`, `halstead.volume`, `halstead.difficulty`, `dependencies.cycles`, `architecture.distance`, `hotspots`, `dead_code`, and AST-based `usages` lookups all run on Julia files. Tree-sitter queries cover `using Foo`, `using Foo, Bar`, `using Foo.Bar`, `using Foo: a, b`, `import Foo`, and `import Base: show`. Abstract-type detection uses `abstract type X end`. New `tree-sitter-julia >= 0.21.0` runtime dependency. See `docs/JULIA.md` for the full status sheet, including known deferrals (short-form functions, do-blocks, CK class metrics) and calibration guidance.
- New `_NpathLangConfig.body_skip_types` field and `_npath_of_flat_body` helper. Lets the npath kernel walk languages whose tree-sitter grammars have no block-wrapper node (Julia today; potentially Lua, some Ruby shapes later). Default value is the empty set so existing languages are unaffected.

### Changed

- **Repository layout: `_aux/` umbrella replaced with substrate-named subpackages.** Discovery primitives now live under `slop._fs/` (fd), `slop._text/` (ripgrep), `slop._ast/` (tree-sitter, plus `treesitter` helpers). Cross-tool primitives (`usages`, `hotspots`, `prune`, `git`) live under `slop._compose/`. Structural metric kernels (`ccx`, `ck`, `npath`, `halstead`, `deps`, `robert`) live under `slop._structural/`. Cross-cutting plumbing (`subprocess`, `doctor`) lives under `slop._util/`. Apache-2.0 attribution for the vendored kernel tree moves from `_aux/LICENSE` to `KERNELS_LICENSE` at the slop package root. Internal-only change; no public API affected. NOTICE, READMEs, CLAUDE.md, `.slop.toml` exclude list, and the ruff `extend-exclude` list all updated to point at the new paths.
- Language tables in README, src/README, SETUP.md, and the CONFIG.md `packages` section now include Julia and document the deferrals.

### Limitations

- Julia short-form functions (`f(x) = x + 1`) are not detected as functions by the structural kernels — they parse as `assignment` nodes with a `call_expression` LHS, not `function_definition`. Same gap for operator-method definitions (`+(a, b) = ...`).
- Julia `do`-blocks (`map(xs) do x ... end`) roll into the enclosing function rather than counted separately.
- Julia `npath` counts top-level branches but under-counts nested control flow inside `elseif`/`else` clause bodies. Treat the number as a lower bound.
- Julia `class.*` (CK CBO/DIT/NOC) is deferred. Same posture as Go and Rust, which also ship without these.

## [0.6.1] - 2026-04-18

**Released to PyPI** on 2026-04-18 as `agent-slop-lint==0.6.1`. Tag: [`v0.6.1`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.6.1).

### Fixed

- **Bundled agent skill's `validate` command** (`skill.sh` / `skill.ps1`, installed via `slop skill <dir>`) used to fail on every slop-only install with `error: aux not found` and tell users to run `./scripts/install.sh`. The `aux` binary is not installed by `pip install agent-slop-lint` and was not a runtime dependency of slop post-0.5.0, so this was a broken instruction. `validate` now checks for `slop` only and points users at `pip install agent-slop-lint` or the install script.
- **`orphans` rule JSON output.** The `next_steps.verify_command` field used to emit `aux usages <symbol> --root <root>`, referencing a command slop does not ship. Replaced with `rg <symbol> <root>` (ripgrep is already a required slop system dependency). The accompanying `message` string now mentions "trace with ripgrep" rather than "trace with `aux usages`".
- Rule-file module docstrings (`complexity.py`, `class_metrics.py`, `dead_code.py`, `dependencies.py`, `hotspots.py`) and `preflight.py` no longer describe their kernels as "aux X_kernel"; they now say "the vendored X_kernel" to match post-0.5.0 reality.
- `docs/SETUP.md` troubleshooting entry for missing system tools no longer references `aux doctor` or `aux curl`; it points at `slop doctor` and a direct install hint for the three system binaries slop uses.

## [0.6.0] - 2026-04-18

**Released to PyPI** on 2026-04-18 as `agent-slop-lint==0.6.0`. Tag: [`v0.6.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.6.0).

### Added

- **`packages` rule now runs on every language slop supports.** Previously `packages` (Martin's Distance from the Main Sequence) was Go and Python only. The underlying `robert_kernel` now has abstract/concrete type detection for Java (`interface`, `abstract class`, `record`), C# (`interface`, `abstract class`, `struct`, `record`), TypeScript (`interface`, `abstract class`), Rust (`trait`, `struct`, `enum`), and JavaScript (all classes counted concrete because the language has no abstract/interface construct). Both the tree-sitter AST path and the regex fallback are implemented per language. See CONFIG.md for per-language semantics and the JavaScript "Zone of Pain by default" caveat.

### Changed

- Documentation cleanup. Removed every remaining claim that `slop` depends on the external `aux-skills` package at runtime (it does not since 0.5.0). README's "Architecture" section now describes the kernels as shipped inside the wheel. SETUP.md no longer says `pip install agent-slop-lint` pulls in `aux-skills`. CLAUDE.md rewritten along the same lines. NOTICE's stale "COMPUTATIONAL BACKEND" block removed and the vendor-code path updated to reflect the 0.5.0 restructure. `_aux/util/doctor.py` install hints for `tree-sitter` and `git` now point at `agent-slop-lint` and `slop hotspots` respectively rather than the pre-vendor `aux-skills` and `aux delta`. Optional-Python-packages block (for the aux curl kernel, which slop does not ship) removed. `_aux/__init__.py` docstring reworded to describe what the subpackage is; attribution remains in NOTICE and the vendored LICENSE where Apache 2.0 requires it.
- Language support table in README and SETUP.md updated to mark `packages` as `yes` for Java, C#, TypeScript, JavaScript, and Rust. CONFIG.md `packages` section rewritten to document the per-language abstract-type conventions and the JavaScript caveat.

### Upgrade notes

- If you run slop on a codebase containing Java, C#, TypeScript, JavaScript, or Rust, the `packages` rule will now produce output where it previously returned nothing. `packages` is `severity = "warning"` by default, so this does not convert passing builds to failing builds without a config change. If the new coverage is noisy on your JS-only project (see caveat above), the quickest silencer is `[rules.packages]\nenabled = false` in your `.slop.toml`.
- `pyproject.toml` without a `[tool.slop]` section no longer halts slop's upward config walk (this landed in 0.5.0; called out here again because the implication for nested-project layouts is subtle). If a subproject pyproject was intentionally shielding a monorepo `.slop.toml`, add an explicit `[tool.slop]` table to keep that behavior.

## [0.5.0] - 2026-04-17

**Released to PyPI** on 2026-04-17 as `agent-slop-lint==0.5.0`. Tag: [`v0.5.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.5.0).

### Added

- **Two new complexity metrics exposed as rules**, both from well-cited prior art:
  - `halstead.volume` (V > 1500) and `halstead.difficulty` (D > 30), from Halstead's (1977) Software Science. Volume catches functions with high information content; Difficulty catches functions with dense operator/operand reuse. These cover the "moderate CCX but many distinct symbols" case that McCabe's cyclomatic complexity misses.
  - `npath` (NPath > 400), from Nejmeh (1988). Counts acyclic execution paths. Unlike CCX (additive), NPath is multiplicative, so ten sequential independent `if` statements produce CCX=11 but NPath=1024. This is the specific pattern agents produce when they dispatch on multiple flags.
- `CHANGELOG.md` (this file) documenting release history going forward. Historical entries for 0.1.0 through 0.4.0 are summaries, not exhaustive.
- CONFIG.md now has a "Note on default thresholds" section at the top documenting every default that diverges from its cited source, with rationale.

### Changed

- **slop is now self-contained.** The metric kernels previously imported from `aux-skills` on PyPI are vendored under `src/cli/slop/_aux/` (Apache-2.0 attributed in `NOTICE` and `src/cli/slop/_aux/LICENSE`). The `aux-skills` runtime dependency is removed; `pip install agent-slop-lint` now installs a single package. aux-skills was pre-1.0 and every kernel slop depended on had been modified in the last 90 days, so the external pin was absorbing breaking-change risk on a cadence slop did not control.
- **Repo layout.** The Python project is now under `src/` (with `src/pyproject.toml`, `src/cli/slop/` for the package, and `src/tests/` for tests). The repo top-level now contains only docs, scripts, skills, LICENSE, NOTICE, README, CHANGELOG, `.slop.toml`, and `.github/`. Dev workflow requires `cd src` before `uv sync` / `uv run pytest` / `uv build`. CI workflows set `working-directory: src` on the relevant steps.
- **Three default thresholds tuned** for contemporary and agentic practice. See CONFIG.md "Note on default thresholds" for per-rule rationale:
  - `complexity.weighted`: WMC > 50 → **WMC > 40** (tighter; closer to Fowler/Martin era advice, catches god-class drift earlier).
  - `halstead.volume`: V > 1000 → **V > 1500** (looser; 1000 flags legitimate orchestration functions, 1500 still flags the pathological three-responsibilities-fused case).
  - `npath`: NPath > 200 → **NPath > 400** (looser; Nejmeh's 1988 ceiling predates modern CLI dispatch — honest `click`/`argparse` main functions sit at NPath 256-512 without being rot).
- **Profiles also re-calibrated** to maintain their semantic relationship to the new defaults:
  - `lax`: WMC 100 → 80, Volume 1500 → 3000, NPath 500 → 1000.
  - `strict`: unchanged (already stricter than the new defaults).
- **Config discovery tweaked.** `_discover_config` now walks past a `pyproject.toml` that has no `[tool.slop]` table rather than stopping there. This lets sub-project pyproject files (like the new `src/pyproject.toml` in this repo) coexist with a repo-root `.slop.toml` in monorepos and nested layouts. Matches how ruff and mypy behave in practice.

### Removed

- `aux-skills` runtime dependency (vendored in; see above).
- `tool.uv.sources` override pointing at a sibling `../aux/cli` path. Development no longer depends on a locally-cloned aux repo.

### Upgrade notes

- Existing `.slop.toml` configs keep working. If you relied on explicit `weighted_threshold`, `volume_threshold`, or `npath_threshold` values, they take precedence over the new defaults.
- If you did NOT set those three thresholds explicitly and your codebase sits in the changed ranges, expect a different violation count on first run after upgrading. WMC went tighter (more violations likely); Volume and NPath went looser (fewer violations likely).
- Users in monorepos with `pyproject.toml` at a sub-project level AND a repo-root `.slop.toml`: discovery will now correctly find the root config instead of halting at the sub-project pyproject. If this changes the behavior you rely on, add an explicit `[tool.slop]` table to the sub-project pyproject.
- The `README.md` and `LICENSE` are tracked both at repo root (for GitHub) and inside `src/` (for PyPI, a hatchling constraint). Keep them in sync when editing.

## [0.4.0] - 2026-04-16

**Released to PyPI** on 2026-04-16 as `agent-slop-lint==0.4.0`. Tag: [`v0.4.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.4.0).

### Added

- `slop doctor` subcommand. Reports availability of `fd`, `rg`, and `git` so users can diagnose missing system dependencies before touching configuration.
- Preflight system-binary check runs automatically before `slop lint` and `slop check`. Missing required binaries produce an explicit error block and exit code 2 rather than silently returning zero files analyzed. Fixes a failure mode where `slop lint` on a machine without `fd` (notably some macOS setups) reported `✓ clean` with no violations.
- Upward config discovery. `slop lint` walks from the current directory toward the filesystem root looking for `.slop.toml` or `pyproject.toml` with `[tool.slop]`, matching ruff/mypy convention. `root` keys in a discovered config now resolve relative to the config file's directory, not CWD.
- Per-rule errors surfaced in human output (previously only JSON). Categories whose rules produced errors now show the error line and the status footer reads `ERROR`.

### Changed

- "Zero files analyzed" now renders as `⚠ no files matched` (yellow warning) rather than `✓ clean`, so genuinely empty scans cannot be mistaken for passing scans.
- A rule that produced errors and no violations is now coerced from `pass` to `error` in the engine layer, so silent failures cannot render as clean.
- `format_human` refactored from a monolith to named helpers with a `_CategoryAgg` dataclass. Dogfood complexity now within slop's own thresholds.

## [0.3.1] - 2026-04-13

**Released to PyPI** on 2026-04-13 as `agent-slop-lint==0.3.1`. Tag: [`v0.3.1`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.3.1).

### Added

- `slop hook` subcommand to install or remove a git pre-commit hook that runs `slop lint --output quiet`.

## [0.3.0] - 2026-04-13

**Released to PyPI** on 2026-04-13 as `agent-slop-lint==0.3.0`. Tag: [`v0.3.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.3.0).

### Added

- `slop skill <dir>` subcommand to copy the bundled agent skill into any directory (for Claude Code / Cursor / other agents).
- `slop init [default|lax|strict]` profile selection.
- `docs/CONFIG.md` rule-by-rule configuration reference.
- `docs/SETUP.md` install-configure-integrate-verify guide.
- `llms.txt` for agent-friendly project discovery.

## [0.2.0] - 2026-04-12

**Released to PyPI** on 2026-04-12 as `agent-slop-lint==0.2.0`. Tag: [`v0.2.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.2.0).

### Changed

- Hotspot metric moved to LOC-delta churn proxy (was commit count) and defaults tightened to a 14-day window (was 90d), calibrated for agentic code generation timescales.
- `aux-skills` pulled from PyPI rather than a sibling git path (internal-dev convenience).

## [0.1.0] - 2026-04-10

**Released to PyPI** on 2026-04-11 as `agent-slop-lint==0.1.0`. Tag: [`v0.1.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.1.0).

### Added

- Initial release. Ten rules across six categories: `complexity.cyclomatic`, `complexity.cognitive`, `complexity.weighted`, `hotspots`, `packages`, `deps`, `orphans`, `class.coupling`, `class.inheritance.depth`, `class.inheritance.children`.
- Backed by `aux-skills` kernels (tree-sitter, ripgrep, fd, git).
- `slop lint`, `slop check`, `slop rules`, `slop init`, `slop schema` subcommands.
- Human, JSON, and quiet output formats.
- `.slop.toml` and `pyproject.toml [tool.slop]` config support.
- PyPI distribution as `agent-slop-lint`.

[Unreleased]: https://github.com/JordanGunn/agent-slop-lint/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.7.1...v0.9.0
[0.7.1]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.1.0
