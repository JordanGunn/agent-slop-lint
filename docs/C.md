---
status: shipped
stability: first cut
ship_state: structural rules supported; class metrics N/A by design
updated: 2026-05-05
---

# C support

C (`.c`, `.h`) is a first-class language for slop's structural,
information-theoretic, and lexical rules. Add it to your `.slop.toml`
`languages` list or pass `--language c` on the CLI.

## What is supported

| Rule | C status | Notes |
|---|---|---|
| `structural.complexity.cyclomatic` (McCabe CCX) | full | Counts `if` / `for` / `while` / `do` / `case_statement` / ternary plus `&&` / `||` short-circuits. Pure-virtual / template / overload concerns are C++-only. |
| `structural.complexity.cognitive` (Campbell CogC) | full | Same decision and nesting nodes; `case_statement` is treated as a compensating decision (logically same depth as the enclosing switch). |
| `structural.complexity.npath` (Nejmeh NPATH) | full | Sequential `if`s multiply, switch cases sum. The `switch_body_types` config field added in v1.0.1 lets the kernel descend through `compound_statement` between switch and cases — same fix also repaired Java and C# silently-broken switch counting. |
| `information.volume` / `information.difficulty` | full | Operator and operand tables enumerate C keywords (`if`, `else`, `while`, `for`, `switch`, ...) and tree-sitter-c symbol leaf types (`+`, `==`, `&&`, `->`, ...). |
| `structural.deps` | best-effort | Tree-sitter queries cover `#include "foo.h"` (local) and `#include <stdio.h>` (system). System includes are treated as external (out of graph). Local includes resolve relative to the importing file's directory; the kernel's index also matches by full filename so sibling and subdirectory layouts work. **Does not follow `-I` paths**: slop has no compiler context. Codebases that rely on include directories rather than relative paths will see incomplete edges. Same posture as Rust deps. |
| `structural.packages` (Martin's I/A/D′) | yes, with caveat | Concrete-type counter sums named `struct_specifier`, `union_specifier`, `enum_specifier`, and `type_definition` declarations (definition-only, not references). C has no abstract construct, so **abstractness is always 0** and packages with `Ca > 0` will land in the Zone of Pain. Default `severity = "warning"` (same posture as JavaScript). |
| `structural.hotspots` | full | Composes `structural.complexity.cyclomatic` plus git churn; rides on the CCX layer. |
| `structural.orphans` | full | Definition queries cover `function_definition`, `struct_specifier`, `enum_specifier`, `union_specifier`, `type_definition` (function-pointer typedefs included). |
| `structural.god_module` | full | Counts top-level `function_definition`, `type_definition`, `struct_specifier`, `union_specifier`, `enum_specifier`. |
| `structural.duplication` (clone density) | full | Function-body fingerprinting on `function_definition` nodes. |
| `structural.redundancy` (sibling calls) | full | New AST scanner; matches sibling top-level `function_definition` nodes that share ≥3 non-stdlib callees. C stdlib (malloc/printf/strcpy/...) is filtered to suppress noise. |
| `structural.local_imports` | yes | Flags `preproc_include` nested inside a `function_definition` body — rare but a real anti-pattern in C. |
| `structural.types.escape_hatches` (any-type density) | yes, with caveat | Escape-hatch pattern is `void *`; annotation-density pattern is regex over C type-prefixed declarations (calibrated tentatively — may flag heavily on macro- or `const`-laden code). Default `severity = "warning"`. |
| `structural.types.hidden_mutators` (out-parameters) | yes | Detects non-`const` pointer parameters mutated via `*p = X`, `p->x = Y`, or `p[i] = Z`. `const T *p` is excluded by design (read-only data is the explicit contract). The `(*p)++` pattern (update_expression on parenthesised pointer_expression) is not detected — out of scope for v1.0.1. |
| `structural.types.sentinels` (stringly-typed) | yes | Flags `char *` / `const char *` parameters whose name matches the established sentinel list (`mode`, `kind`, `type`, `level`, `state`, ...). The advisory message text references "Literal[...] or Enum" — the suggested remedy in C would be a typedef'd enum, not a Python `Literal`. Wording will be language-aware in a follow-up. |
| `information.magic_literals` | full | Counts distinct non-trivial `number_literal` nodes per function. |
| `information.section_comments` | full | Detects divider patterns `/* === ... ===`, `/* --- ... ---`, `// === ... ===` etc. inside function bodies. |
| `lexical.stutter` | full | Function scope only; C has no class concept so the class-scope check is empty by design. |
| `lexical.verbosity` / `lexical.tersity` | full | Reuses the language-agnostic identifier-token splitter. |
| `structural.class.*` (CK CBO/DIT/NOC/WMC) | **N/A by design** | C has no class concept. Structs are data-only with no methods or inheritance. The kernel silently produces no results for `.c` / `.h` files (returns empty result with no error). Same posture as Julia for CK metrics. |

## Why CK metrics aren't shipped for C

The Chidamber-Kemerer suite is defined over object-oriented entities: a
class owns methods, classes form an inheritance tree, methods can be
overridden. C has none of those. A `struct` is pure data (no methods,
no inheritance, no method dispatch). Functions that operate on a struct
are siblings of the struct, not members of it. There is no analog of
DIT (depth in inheritance tree) or NOC (number of children) because
there is no inheritance tree. CBO (coupling between objects) could be
defined as the count of distinct types referenced in a function's
parameter list and body, but interpreting that against thresholds tuned
for Java would mislead more than it would help.

We follow the same posture as for Julia (multiple dispatch) and Go
(receiver-based dispatch): when a precise mapping is absent, ship
silence rather than misleading numbers.

## `structural.deps` best-effort posture

The C deps kernel resolves only relative includes: `#include "foo.h"`
matches `foo.h` in the same directory, and `#include "subdir/foo.h"`
matches a sibling `subdir/foo.h`. It does not follow:

- `-I` paths from a Makefile, CMake, or compile_commands.json.
- System include roots (`/usr/include`, `/usr/local/include`, ...).
- Conditional compilation (`#if`, `#ifdef`).
- Macro-substituted include paths.

A user codebase that relies on `-I` paths instead of co-located
headers will see headers reported as external (system-style). This is
a deliberate trade-off: parsing a C build system is out of scope for
slop. If you want a complete include graph, run a tool that has
compiler context (Bear / compiledb / clang's `-MMD` output) and feed
it externally; slop's deps is calibrated for the structural-discipline
question "does this codebase have any cycles in the includes I can
see?", not for full reachability analysis.

## `structural.packages` Zone-of-Pain caveat

C has no `interface`, `abstract class`, `trait`, or any other
abstraction marker in the language itself. Every type definition
(struct, union, enum, typedef) is concrete. Therefore A (abstractness)
is always 0 for any C package, and Martin's distance-from-the-main-
sequence formula `D' = |A + I - 1|` reduces to `|I - 1|`. A C package
with no afferent coupling has `I = 1` and `D' = 0` (clean). A C
package with afferent coupling has `I < 1` and `D' > 0`, landing
toward the Zone of Pain.

This is honest reporting — C genuinely has no abstraction story at
the language level. The default `severity = "warning"` (matching
JavaScript) keeps the rule advisory rather than gating the build.
Treat it as a coupling-asymmetry signal, not as a refactoring demand.

## How language support is structured

Adding a language to slop is a tabular exercise. The kernels that
touch tree-sitter have per-language config:

- `_ast/treesitter.py` — `GRAMMAR_MAP` (language → tree-sitter package),
  `EXT_LANGUAGE_MAP` (extension → language).
- `_structural/ccx.py`, `_structural/npath.py`, `_structural/halstead.py`
  — per-language `_LANG_CONFIG` dataclass listing the tree-sitter node
  types that count as functions, decisions, operators, etc., plus
  `_LANG_GLOBS` for the file-discovery glob.
- `_structural/ck.py` — C is **intentionally absent** (see the comment
  block at the top of `_LANG_CONFIG`).
- `_structural/deps.py` — `IMPORT_QUERIES` (tree-sitter queries) and
  `TEXT_IMPORT_REGEXES` (fallback) per language, plus an extension-to-
  language map in `_detect_file_language`.
- `_structural/robert.py` — `_LANG_GLOBS` plus the per-language
  abstractness-counting branch in `_compute_abstractness_ast` /
  `_compute_abstractness_text`.
- `_compose/usages.py` — `DEFINITION_QUERIES` per language (used by
  `prune` and `usages`).
- Smaller kernels (`magic_literals`, `section_comments`, `god_module`,
  `clone_density`, `local_imports`, `sibling_calls`, lexical) — plain
  per-language frozenset dicts plus `_LANG_GLOBS`.

C uses the same `name_extractor` Callable pattern that Julia
established for kernels with `_LangConfig` dataclasses. Tree-sitter-c
exposes the function name through the declarator chain
(`function_declarator → identifier`, optionally wrapped by
`pointer_declarator` for pointer return types) rather than a `name`
field, so the default extractor returns `<anonymous>` for every C
function. The C-specific extractor in `ccx.py` / `npath.py` /
`halstead.py` walks the declarator chain. The smaller kernels' generic
`_fn_name` helper has the same chain-walking shim inlined.

## Calibration thresholds for C

The shipped defaults — McCabe CCX > 10, NPath > 400, Halstead Volume >
1500 — were calibrated on Python, JavaScript, and Go corpora. They
have not been re-calibrated against a C corpus. Expected deviations:

- C functions tend to run **higher** in CCX than typical Python on the
  same problem (no convenient list comprehensions, dict dispatch, or
  exception handling — it's all explicit branches). The defaults will
  flag more aggressively on C than on Python at the same threshold.
- Halstead operand counts are inflated by C's verbose type system
  (`unsigned long long int x;` produces several operands per
  declaration). Volume thresholds may need tightening.
- Section-comment dividers in C are most often `/* === ... === */`
  block-style rather than the `// === ... === ` line-style common in
  Go/Java/C#. The pattern was widened in v1.0.1 to match block-style
  too.

If you're using slop on a C codebase, expect to tune thresholds once
you've seen the distribution. Run `slop lint --output json` and look
at the per-function values before settling on a threshold.

## Tree-sitter grammar pin

`tree-sitter-c >= 0.21.0`. Node type names that the kernels depend on:

- Function shape: `function_definition`, `function_declarator`,
  `pointer_declarator`, `identifier`.
- Control flow: `if_statement`, `else_clause`, `for_statement`,
  `while_statement`, `do_statement`, `switch_statement`,
  `compound_statement`, `case_statement`, `conditional_expression`.
- Operators: `binary_expression` with operator field returning a leaf
  whose type is the operator string (`&&`, `||`, etc.).
- Types: `struct_specifier`, `union_specifier`, `enum_specifier`,
  `type_definition`, `type_identifier`.
- Includes: `preproc_include`, `string_literal` (with `string_content`
  child), `system_lib_string`.

If queries start failing after a tree-sitter-c upgrade, the candidates
are the declarator chain shape (`function_declarator → declarator
field`), the switch wrapper (`compound_statement` between
`switch_statement` and `case_statement`), and the include path-child
type names.

## What's not yet supported

- **C++** (`.cpp`, `.hpp`, `.cc`, `.cxx`) is wired in at the AST layer
  (tree-sitter-cpp grammar dependency, extension map) but no kernel
  registers it. Tracked for v1.0.2. Templates, out-of-line method
  definitions (`void Foo::bar() {}`), `base_class_clause`-based
  inheritance, namespaces, lambdas, and `final` are the substantive
  shape work.
- **Macro-aware analysis.** `#define` macros that expand to control
  flow are invisible to the AST kernels (the AST sees the
  `preproc_function_def` shell, not the expansion). Same limitation as
  every other tree-sitter-based tool.
- **`(*p)++` mutation pattern** in `structural.types.hidden_mutators`.
  Only `*p = X`, `p->x = Y`, and `p[i] = Z` are currently flagged.
  Update-expression handling is a follow-up.
