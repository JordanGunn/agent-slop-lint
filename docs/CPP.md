---
status: shipped
stability: first cut
ship_state: full rule set including CK class metrics
updated: 2026-05-05
---

# C++ support

C++ (`.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx`) is a first-class language
for slop's structural, information-theoretic, and lexical rules,
**including** the CK class-metrics suite. Add it to your `.slop.toml`
`languages` list or pass `--language cpp` on the CLI.

`.h` headers are still classified as **C** by default (see
`docs/C.md`). Most C++ headers use `.hpp` / `.hxx`. If your codebase
uses `.h` for C++ headers exclusively, override `languages` and globs
explicitly in `.slop.toml`.

## What is supported

| Rule | C++ status | Notes |
|---|---|---|
| `structural.complexity.cyclomatic` (McCabe CCX) | full | Decision nodes extend C with `for_range_loop`, `try_statement`, `catch_clause`. Templates are unwrapped via `template_declaration`. Lambdas count as anonymous functions named `<lambda>`. Operator overloads named by their symbol (`==`, `+`, etc.). Destructors named `~ClassName`. Out-of-line methods (`void Foo::bar() {}`) named with the rightmost identifier (`bar`). |
| `structural.complexity.cognitive` (Campbell CogC) | full | Same node set as cyclomatic; `case_statement` is a compensating decision. |
| `structural.complexity.npath` (Nejmeh NPATH) | full | Sequential `if`s multiply, switch cases sum, try/catch contributes try-body + handler-body paths, range-for is a loop. The `switch_body_types` and `definition_unwrap_types` config fields handle C++'s `compound_statement` switch wrappers and `template_declaration` wrappers respectively. |
| `information.volume` / `information.difficulty` | full | Operator/operand tables enumerate the C++ keyword set (`class`, `template`, `namespace`, `try`, `catch`, `throw`, `new`, `delete`, `auto`, `nullptr`, `constexpr`, casts, ...) plus C++ symbols (`::`, `<=>`, `->*`, `.*`, etc.). |
| `structural.deps` | best-effort | `#include "foo.hpp"` resolves relative to the source-file directory; `#include <vector>` treated as external. Same posture as C deps — **does not follow `-I` paths**. The kernel's filename index also matches by full filename so subdirectory layouts work. |
| `structural.packages` (Martin's I/A/D′) | full | A class is **abstract** iff (a) it has at least one pure-virtual method (`virtual T f() = 0;`), and (b) it is not declared `final`. All other classes are concrete. Structs, unions, enums, and typedefs are concrete. Default `severity = "warning"`. |
| **`structural.class.complexity` (WMC)** | **full** | Per-class WMC is the sum of method CCXs. Methods include in-class definitions (declarator chain ends in `field_identifier`) and out-of-line definitions (`void Foo::bar() {}` — declarator ends in `qualified_identifier`). The kernel runs a second-pass walker (`_collect_cpp_outofline_methods`) over each file to attribute out-of-line method CCX back to its class. |
| **`structural.class.coupling` (CBO)** | **full** | Counts distinct types referenced inside the class body (member fields, method parameters, return types). |
| **`structural.class.inheritance.depth` (DIT)** | **full** | Walks the `base_class_clause` graph. Multiple inheritance contributes the deepest path. |
| **`structural.class.inheritance.children` (NOC)** | **full** | Counts direct subclasses (the inverse map of `base_class_clause` parents). |
| `structural.hotspots` | full | Composes `structural.complexity.cyclomatic` + git churn. |
| `structural.orphans` | full | Definition queries cover function variants (plain, in-class, out-of-line, pointer/reference return), class/struct/union/enum/typedef definitions, and namespace_definitions. |
| `structural.god_module` | full | Counts `function_definition`, `class_specifier`, `struct_specifier`, `union_specifier`, `enum_specifier`, `template_declaration`, `namespace_definition`, `type_definition`. |
| `structural.duplication` (clone density) | full | Function-body fingerprinting; lambdas included. |
| `structural.redundancy` (sibling calls) | partial | Top-level free functions only. Class methods (in-class or out-of-line) are not analysed for sibling redundancy because their caller relationship is structurally different from free-function siblings. C++ stdlib idioms (`malloc`, `printf`, `std::move`, `make_unique`, ...) are filtered to suppress noise. |
| `structural.local_imports` | yes | Flags `preproc_include` or `using_declaration` nested inside a function body. Rare but a real anti-pattern. |
| `structural.types.escape_hatches` | yes, with caveat | Escape pattern matches `void *` and `std::any`. The annotation regex extends C's pattern with C++ qualifiers (`constexpr`, `mutable`, `consteval`), references via `&`, namespaced types (`std::vector<...>`), and templated types. Calibration is tentative; default `severity = "warning"`. |
| `structural.types.hidden_mutators` | yes | Detects mutations through non-`const` pointer parameters (`*p = X`, `p->x = Y`, `p[i] = Z`) AND non-`const` reference parameters (`r = X`, `r.field = Y`, `r[i] = Z`). `const T* p` and `const T& r` are excluded by design. |
| `structural.types.sentinels` | yes | Flags `char *`, `const char *`, `std::string`, `std::string_view`, and their wide-string variants when the parameter name (lowercased, trailing `_` stripped) is in the sentinel list. The advisory message text references "Literal[...] or Enum" — the suggested remedy in C++ would be a typed enum (`enum class`), not a Python `Literal`. Wording will be language-aware in a follow-up. |
| `information.magic_literals` | full | Counts distinct non-trivial `number_literal` nodes per function. |
| `information.section_comments` | full | Detects `/* === ... */` block-style and `// === ... ===` line-style dividers inside function bodies. |
| `lexical.stutter` | full | Function and class scopes both checked; namespace scopes also count as class-equivalent scope for stutter. |
| `lexical.verbosity` / `lexical.tersity` | full | Reuses the language-agnostic identifier-token splitter. Lambda parameter names (often single letters: `x`, `y`, `it`) may push tersity scores higher than expected on lambda-heavy code. |

## Why class metrics work for C++ but not for C

C has structs, but a C struct is data-only — no methods, no inheritance, no virtual dispatch. CK metrics are defined over object-oriented entities, so they have no meaningful definition for C; slop silently skips C files for `structural.class.*`.

C++ has classes, single and multiple inheritance, abstract bases via pure-virtual methods, `final` to close inheritance, and out-of-line method definitions that bind back to a class via `Foo::method` qualified identifiers. Every CK metric maps directly. v1.0.2 ships them.

## Out-of-line method attribution

A typical C++ codebase declares a class in `foo.hpp` and defines its methods in `foo.cpp`:

```cpp
// foo.hpp
class Foo {
public:
    void bar();
    int baz() const;
};

// foo.cpp
void Foo::bar() { ... }
int Foo::baz() const { return 42; }
```

The `.cpp` file's `function_definition`s are at file scope (outside any class body), so the standard "WMC = sum of method CCXs in the class body" computation would attribute zero CCX to `Foo`. v1.0.2 fixes this with a second-pass walker that catalogues every top-level `function_definition` whose declarator chain ends in `qualified_identifier`, parses the class name out of the qualified path, and adds the function's CCX to the matching class's WMC.

**Limitation: bare class name match.** The current attribution uses the bare class name (everything to the left of `::`), ignoring the namespace qualifier. Two classes named `Foo` in different namespaces — `ns_a::Foo` and `ns_b::Foo` — would collide; one would receive both classes' WMC. This is a known approximation. Most codebases avoid name reuse across namespaces; for the rare ones that don't, the WMC error is bounded to the methods of the colliding classes.

**Limitation: cross-translation-unit definitions.** A method whose class is declared in a header file outside the scanned set (or vice versa: class in the scan, method definitions in an unscanned file) won't be attributed. Same posture as deps without `-I` paths.

## `structural.deps` best-effort posture

Identical to C: relative `#include "foo.hpp"` resolves to a peer file; system `#include <vector>` is treated as external. `-I` paths are not followed. Conditional compilation (`#if`/`#ifdef`) is invisible.

## `structural.packages` Zone-of-Pain caveat

C++ has a real abstractness story (interfaces are pure-virtual classes, `final` closes the door), so `D' = |A + I - 1|` produces meaningful values. Default `severity = "warning"` is retained for symmetry with C and JavaScript and because A=0 is still common in legacy C++ (header files containing only structs and free functions).

## Calibration thresholds for C++

Defaults are tuned for Python/JS/Go and not re-calibrated against a C++ corpus. Expected deviations:

- C++ functions tend to run **higher** on CCX than Python on the same problem (no comprehensions, exception handling is explicit branches in NPath terms, multi-branch error returns are common idioms).
- Halstead operand counts are inflated by C++'s verbose type system (templates, `const`, `&`, `::` all contribute operands).
- `lexical.tersity` may flag lambda-heavy functions where short parameter names (`x`, `y`, `it`) are idiomatic.
- `structural.duplication` may catch boilerplate getter/setter pairs that are intentionally identical across classes (consider raising the threshold or adding waivers).

If you're using slop on a C++ codebase, run `slop lint --output json` and look at the per-function distribution before settling on thresholds.

## Tree-sitter grammar pin

`tree-sitter-cpp >= 0.21.0`. Node-type names that the kernels depend on:

- Function shape: `function_definition`, `function_declarator`, `pointer_declarator`, `reference_declarator`, `parenthesized_declarator`, `lambda_expression`, `template_declaration`.
- Function-name carriers: `identifier`, `field_identifier`, `qualified_identifier`, `operator_name`, `destructor_name`.
- Class shape: `class_specifier`, `struct_specifier`, `field_declaration_list`, `field_declaration`, `base_class_clause`, `access_specifier`, `virtual_specifier`.
- Control flow: `if_statement`, `else_clause`, `for_statement`, `for_range_loop`, `while_statement`, `do_statement`, `switch_statement`, `compound_statement`, `case_statement`, `try_statement`, `catch_clause`, `conditional_expression`.
- Includes: `preproc_include`, `string_literal` (with `string_content`), `system_lib_string`.
- Types and namespaces: `namespace_definition`, `namespace_identifier`, `type_definition`, `type_identifier`, `enum_specifier`, `union_specifier`.

If queries fail after a tree-sitter-cpp upgrade, the candidates are the
declarator chain (`function_declarator → declarator field`), the
`base_class_clause` shape, the `virtual_specifier "final"` location,
and the `qualified_identifier` parsing for out-of-line methods.

## What's not yet supported

Each item is tagged with **why** it isn't shipped — distinguishing deferrals (solvable, just not done) from genuinely structural limits (bounded by the underlying tooling).

### Deferred (solvable, queued for a follow-up)

- **Bare-name namespace collisions in WMC out-of-line attribution.** `ns_a::Foo::bar()` is matched against class `Foo` ignoring the namespace, so two `Foo` classes in different namespaces can collide. *Solvable* by tracking each class declaration's enclosing `namespace_definition` during the class-collection pass and matching against the full qualified path. ~50-100 lines plus tests. Deferred because real-world C++ rarely reuses class names across namespaces; the WMC error is bounded to the colliding methods.
- **Diagnostic when out-of-line methods can't bind to a class.** If `Foo::bar()` is in the scanned set but `class Foo` is not (e.g. header outside the scan), the method's CCX is silently dropped. *Solvable* with a per-file warning surfacing the orphan attributions so the user knows to widen their globs. ~10 lines.
- **C++20/23 grammar features.** `co_await` / `co_yield` / `co_return` are speculatively listed in the Halstead operator table — they'll count if a recent enough `tree-sitter-cpp` emits them, otherwise harmlessly absent. `concepts` (`requires_clause`, `concept_definition`) and `modules` (`module_declaration`) are not yet probed against the installed grammar version; node types may need to be added to the operator/decision sets. *Solvable* with an AST probe against a current grammar wheel.

### Structural (bounded by the substrate)

- **Cross-translation-unit definitions whose declaring header is outside the scan.** slop sees only what's in your `--root` glob set; a method whose class is declared in a header file you didn't scan can't bind back. The diagnostic above narrows the visibility of this gap; widening the scan is the user's call.
- **Macro-aware analysis.** A `#define` macro that expands to control flow is invisible to every tree-sitter-based tool — slop sees the `preproc_function_def` shell, not the expansion. Solving this requires a real preprocessor; out of slop's substrate.
- **`-I` include paths in `structural.deps`.** Same posture as Rust deps. Resolving compiler-context include paths means parsing a build system; out of slop's substrate.

### Scope decisions (intentionally not implemented)

- **Class methods inside `structural.redundancy`.** Sibling-call redundancy is free-function-only on C++ for now. Class methods coordinate behaviour within a class — the redundancy signal is structurally different from free-function siblings, and pretending the same threshold means the same thing would be misleading. Could be reopened with a separate per-class shape if calibration suggests it's useful.
- **`final` on individual methods.** `final` on a class disqualifies abstractness (a `final` class can't be subclassed, so it can't be the abstract endpoint of a hierarchy). `final` on a single method has no effect on any rule today; it's a hint about override safety, not coupling or complexity. No clear metric maps to it.

## Header / source split convention

- `.cpp` / `.cc` / `.cxx` → C++ source files.
- `.hpp` / `.hxx` → C++ header files (always classified as cpp).
- `.h` → **C** by default. If your codebase uses `.h` for C++ headers, set `languages = ["cpp"]` and globs explicitly in `.slop.toml`.

This conservative default avoids reclassifying C codebases that already shipped with v1.0.1.
