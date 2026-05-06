---
status: shipped
stability: first cut
ship_state: full applicable rule set; type-discipline rules silently skip
updated: 2026-05-05
---

# Ruby support

Ruby (`.rb`) is a first-class language for slop's structural,
information-theoretic, and lexical rules, **including the CK
class-metrics suite** with open-class aggregation. Add it to your
`.slop.toml` `languages` list or pass `--language ruby` on the CLI.

## What is supported

| Rule | Ruby status | Notes |
|---|---|---|
| `structural.complexity.cyclomatic` (McCabe CCX) | full | Decision nodes: `if`, `elsif`, `unless_modifier`, `if_modifier`, `while_modifier`, `until_modifier`, `rescue_modifier`, `while`, `until`, `for`, `when`, `rescue`, `conditional` (ternary). Boolean operators: `&&`, `\|\|`, `and`, `or` on `binary` nodes. |
| `structural.complexity.cognitive` (Campbell CogC) | full | Same nodes; `elsif` and `when` are compensating decisions (logically same depth as the enclosing if/case). |
| `structural.complexity.npath` (Nejmeh NPATH) | full | Sequential postfix-ifs multiply, when-clauses sum, rescue contributes a path. Ruby's positional body shape is handled via `body_skip_types` (Julia precedent). |
| `information.volume` / `information.difficulty` | full | Operator/operand tables enumerate Ruby keywords (`def`, `class`, `module`, `if`, `case`, `when`, `begin`, `rescue`, `require`, `include`, `attr_accessor`, ...) and the symbol set including Ruby-unique tokens (`<=>`, `..`, `...`, `=>`, `->`, `&&=`, `\|\|=`). |
| `structural.deps` | best-effort | Tree-sitter query matches `require`, `require_relative`, `load` calls; the kernel's index resolves `require_relative './foo'` to a peer file. `require 'gem_name'` (no `./` prefix) is treated as external. **Does not follow gem `$LOAD_PATH`** — slop has no Ruby runtime context. |
| `structural.packages` (Martin's I/A/D′) | full | Modules are the natural abstract analog (`Module` instances cannot be instantiated, only mixed in via `include`/`extend`). Classes are concrete. Ruby has no `final` keyword. Default `severity = "warning"`. |
| **`structural.class.complexity` (WMC)** | **full, with open-class aggregation** | Per-class WMC is the sum of method CCXs across every `class Foo` re-opening. Ruby's open-class semantics let the same class be redefined in multiple files; `_aggregate_ruby_open_classes` merges them by name into a single CK entity post-WMC, summing method counts and unioning superclasses. See "Open-class aggregation" below. |
| **`structural.class.coupling` (CBO)** | **full** | Counts distinct types referenced inside the class body (member references, method call receivers, mixin targets). Mixed-in module names DO count toward CBO. |
| **`structural.class.inheritance.depth` (DIT)** | **full** | Walks the `superclass` field. Mixins (`include`/`extend`) do NOT count toward DIT — Ruby community convention treats them as composition. CBO captures mixin coupling. |
| **`structural.class.inheritance.children` (NOC)** | **full** | Counts direct subclasses via the inverse `superclass` relation. |
| `structural.hotspots` | full | Composes `structural.complexity.cyclomatic` + git churn. |
| `structural.orphans` | full | Definition queries cover regular methods, singleton methods (`def self.foo`), operator methods (`def ==`), classes, and modules. |
| `structural.god_module` | full | Counts top-level `method`, `singleton_method`, `class`, `module` definitions. |
| `structural.duplication` (clone density) | full | Function-body fingerprinting on `method`, `singleton_method`, `lambda`, `do_block`, `block`. |
| `structural.redundancy` (sibling calls) | partial | Top-level free methods only (Ruby's idiom for "free function" — `def` outside any `class`/`module`). Class methods are not analysed for sibling redundancy. Ruby stdlib idioms (`puts`, `each`, `map`, `attr_accessor`, ...) filtered out. |
| `structural.local_imports` | yes | Flags `require`/`require_relative`/`load` calls inside method bodies. v1.0.3 added a per-language predicate hook (`IMPORT_NODE_PREDICATES`) so the kernel can distinguish require-style calls from ordinary calls. |
| `structural.types.sentinels` (stringly-typed) | yes | Flags method parameters whose name (lowercased, trailing `_` stripped) is in the sentinel list. Ruby has no static type annotations to gate on, so the rule fires on any sentinel-named parameter. The advisory message text references "Literal[...] or Enum" — the suggested remedy in Ruby would be a typed `Symbol` enum or a `Set` constant. Wording will be language-aware in a follow-up. |
| `information.magic_literals` | full | Counts distinct non-trivial `integer` / `float` / `complex` / `rational` literals per method. |
| `information.section_comments` | full | Detects `#`-style dividers inside method bodies. |
| `lexical.stutter` | full | Function and class scopes; namespaces (modules) also count as class-equivalent scope. |
| `lexical.verbosity` / `lexical.tersity` | full | Reuses the language-agnostic identifier-token splitter. |

### Structurally N/A — silent no-op

Two rules don't apply to Ruby and are intentionally not registered:

- **`structural.types.escape_hatches`** (any-type density). Ruby is dynamically typed — every parameter is implicitly `Object`. There is no type system to escape, so "fraction of annotations using an escape-hatch type" has no meaningful definition. Same posture as CK on C (no class concept).
- **`structural.types.hidden_mutators`** (out-parameters). Ruby's parameter-passing is always by reference; every object is mutable. "Callee mutates a parameter" is the language default rather than an anti-pattern. Without a static type system the rule has no signal-to-noise floor; silent no-op.

Both decisions are documented with a comment block in the respective kernel's `_LANG_GLOBS` / `_LANG_CONFIG` location.

## Open-class aggregation

Ruby's open-class semantics let the same class be redefined across multiple files. Each re-opening parses as a fresh `class` node, so each becomes a distinct `_ClassInfo` entry in slop's CK kernel. Without aggregation, a single class redefined in 3 files would produce 3 entries in the output.

v1.0.3's `_aggregate_ruby_open_classes` post-WMC pass merges them by name within the Ruby subset:

- WMC and `method_count` are **summed** (every method definition contributes).
- CBO, DIT, NOC are taken as the **max** (CBO is per-class-instance and may legitimately differ; DIT/NOC are computed once per class name, so max is a safe defense).
- Superclasses are **unioned** (Ruby allows different re-openings to declare different superclasses, though that's pathological — slop reports both).
- The **canonical file:line** is the first-encountered definition.

This means a single output entry like:

```
shapes.rb:21 Circle — WMC 12, methods 5
```

reflects every method of `Circle` across every file that re-opened it, even if no single file contains all 5 methods.

**Limitation: glob-bounded aggregation.** If your `--root` glob covers only some of the files that re-open `Foo`, the aggregated WMC reflects only the visible openings. Widening the scan changes the metric — same posture as deps without `-I` paths.

## Mixin coupling

Ruby mixins (`include MyMod` / `extend MyMod` / `prepend MyMod`) are call-statements inside the class body, not part of the `superclass` field. v1.0.3's posture:

- **CBO**: yes, mixed-in module names count as references (matches the rule's "distinct types referenced" intent).
- **DIT**: no, mixin chains do NOT contribute to inheritance depth.
- **NOC**: no, including a module does not count as "subclassing" it.

The Ruby community is split on whether mixins should count for DIT. The conservative posture (don't) keeps DIT's semantics consistent across languages. A Rails application heavy on `Concern` mixins might surface high CBO without high DIT — that's correct: the modules are coupled in but not inherited from.

## `structural.deps` best-effort posture

- `require_relative './foo'` resolves to a peer `foo.rb`.
- `require_relative '../lib/util'` resolves through directory traversal.
- `require 'gem_name'` (no `./` prefix) is treated as external (gem from `$LOAD_PATH`).
- `load 'config.rb'` resolves the same way as `require_relative`.

slop does **not** follow Ruby's `$LOAD_PATH`, Bundler's `Gemfile`, or `RUBYLIB`. A codebase that adds custom load paths will see those imports as external. Same posture as Rust/C/C++ deps.

## Calibration thresholds for Ruby

Defaults are tuned for Python/JS/Go and not re-calibrated against a Ruby corpus. Expected deviations:

- Ruby methods tend to run **lower** in CCX than Python on the same problem — Ruby idiomatically uses block-style iteration (`.each { ... }`, `.map { ... }`) which slop counts as separate anonymous functions rather than as part of the enclosing method.
- Halstead operand counts are inflated by Ruby's symbol-rich syntax (`@var`, `@@var`, `$var`, `:foo` symbols all contribute distinct operand types).
- `structural.types.sentinels` may produce noise on Rails / DSL-heavy codebases where parameters named `kind`, `mode`, `state` are pervasive idioms. Default `severity = "warning"` keeps it advisory.
- `structural.duplication` may catch boilerplate `attr_accessor` / `def initialize` patterns. Consider raising the threshold on Rails models.

If you're using slop on a Ruby codebase, run `slop lint --output json` and inspect the per-method distribution before settling on thresholds.

## Tree-sitter grammar pin

`tree-sitter-ruby >= 0.21.0`. Node-type names that the kernels depend on:

- Method shape: `method`, `singleton_method`, `lambda`, `do_block`, `block`, `block_body`, `body_statement`.
- Method-name carriers: `identifier`, `operator` (for operator overloads).
- Class / module shape: `class`, `module`, `superclass`, `constant`.
- Control flow: `if`, `elsif`, `else`, `case`, `when`, `while`, `until`, `for`, `begin`, `rescue`, `ensure`, `conditional`, `if_modifier`, `unless_modifier`, `while_modifier`, `until_modifier`, `rescue_modifier`.
- Calls / imports: `call` (with `method:` and `arguments:` fields), `argument_list`, `string`, `string_content`.
- Operands: `identifier`, `instance_variable`, `class_variable`, `global_variable`, `constant`, `integer`, `float`, `complex`, `rational`, `string`, `symbol`.

If queries fail after a tree-sitter-ruby upgrade, the candidates are:
- The `method` / `singleton_method` shape (positional `def`/`self`/`.` then identifier/operator).
- The `superclass` field on `class`.
- The `call` node's `method:` field name.

## What's not yet supported

### Deferred (solvable, queued)

- **Mixin-aware DIT**. Some teams want `include`/`extend` to count toward inheritance depth (the way Ruby `Method.ancestors` includes mixed-in modules). Could be exposed as a per-rule param (`include_mixins=true`) with a follow-up.
- **`define_method` and other metaprogramming**. Methods defined dynamically don't appear as `method` nodes in the AST. Same posture as macro-aware analysis in C/C++ — out of slop's substrate.
- **Sentinel rule message wording.** Currently references "Literal[...] or Enum"; should suggest typed `Symbol` constants for Ruby.

### Structural (bounded by the substrate)

- **Cross-file open-class definitions outside the scan.** If `class Foo` is re-opened in a file outside your `--root` scan, those methods don't aggregate. Slop only sees what's visible.
- **`$LOAD_PATH` / Bundler / `RUBYLIB`** for deps. Requires Ruby runtime context to evaluate; out of substrate.

### Scope decisions (intentionally not implemented)

- **`structural.types.escape_hatches`** and **`structural.types.hidden_mutators`** — silent no-op, see "Structurally N/A" above.
- **Class methods inside `structural.redundancy`.** Sibling-call redundancy is free-function-only on Ruby. Class methods coordinate within a class — different signal from free-function siblings.
- **ERB / template files.** `.rb.erb` files contain mixed Ruby + ERB markup; not a clean parse target.

## Header / source convention

Ruby uses `.rb` for both library and application code. `.rake`, `.gemspec`, `.ru`, etc. are not currently mapped — add them to your globs explicitly if you want them analysed as Ruby.
