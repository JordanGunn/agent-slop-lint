# Language-agnosticism — the grammar-fact contract

> **Status: in progress.** The audit below is verified. Parameter extraction (the
> root silent-failure) is fixed; the remaining grammar facts are tracked as the
> work-list at the bottom.

## The principle

slop's scope hierarchy (`Corpus > Realm > Package > Module > Class > Callable`) is
**semantic**, not lexical. Shared algorithm code (`metrics/`, `rules/`, `scope/carve`)
must never branch on language or hardcode one language's tree-sitter node types. Every
per-language idiom is a **tabular fact on the grammar class** (`ast/grammar/<lang>.py`),
defaulted in `ast/paradigm/base.py`. Overfitting to Python is the failure mode this
document guards against.

### The scope mapping (semantic, not Python's words)

| slop scope | role | resolver | Python | Go | Java | Rust |
|---|---|---|---|---|---|---|
| Realm | distribution root | (carve) | scan root | `go.mod` module | source root | crate |
| Package | dir-level import grouping | `resolve_packages()` | `__init__.py` dir | dir w/ `package x` clause | `package a.b.c;` decl | `mod` / `mod.rs` |
| Module | one source file | — | `.py` | `.go` | `.java` | `.rs` |

Note Go *inverts* Python's words: Go's "package" = a directory (slop **Package**); Go's
"module" = the `go.mod` tree (slop **Realm**). Don't map by name; map by role.

## Verified audit (2026-06-03)

The root finding, **verified by running**: `extract_parameters` returned `()` for Go,
Rust, Java, TypeScript (and every non-Python grammar) — the base helper matched Python
tree-sitter node types (`typed_parameter`/`default_parameter`/`*args`). This silently
dropped every parameter token from the lexicon on all non-Python code. The
"not flagged ≠ clean" class.

Other Python assumptions found (work-list below): hardcoded `self`/`cls`, the
`child_by_field_name("body")` walk, the `{python,javascript,ruby}` dynamic-language
set + `__x__` dunder checks, and the `__init__.py` literals in `carve.py`/`graph/build.py`.

**Resolved since the audit:** the C# tree-sitter wheel did not load at audit time. It
loads and parses now; `tests/test_cli_primitives.py` pins discovery for every
class-bearing grammar, C# included.

## Grammar-fact contract

A grammar supplies (defaults in `base.py`, override where the language differs):

- `extract_parameters(node, content) -> ((name, annotation), ...)` — **done.** Base is
  now language-neutral: a parameter name is an identifier-typed node (the param node
  itself or its identifier children); types are distinct node kinds. Covers
  Python/Go/Rust/Java/TS/JS/Ruby. C-family overrides (`c_style_parameters` — names nest
  in declarators); Julia overrides (`julia_signature_parameters` — params under
  `signature → call_expression → argument_list`).
- `parameter_list_field()` / `parameter_name_node_types()` — tabular knobs for the base.
- `package_init_name()` — the package-marker filename (Python `__init__.py`; `None`
  where there is no init-file convention, and the init branch is skipped). **#40:**
  now also drives the package-init module qualname in `scope/carve` and the
  parent-package name spellings in `graph/build` — both previously hardcoded the
  `"__init__"`/`"__init__.py"` literal in shared code.
- `resolve_packages(root, files)` — the language's package boundary (TODO: Go/Java/Rust).
- `body_field()` / `block_types()` / `body_skip_types()` — **done (delegated).** The
  NPath walk (`complexity._NPathVocab`) resolves the walkable body language-agnostically:
  the named `body_field()` child where it is non-empty; else a `block_types()` wrapper
  child; else the flat-body direct children minus `body_skip_types()`. The old hardcoded
  `child_by_field_name("body")` silently dropped *every Julia callable* (its
  `function_definition` has no body field → `None`).
- `is_dynamic_language()` / `is_special_method(name)` — **done.** Replaced the hardcoded
  `_DYNAMIC_LANGUAGES = {python,javascript,ruby}` set and the `__x__` dunder checks that
  were buried in shared `orphans`. `is_dynamic_language()` lowers orphan confidence one
  tick (runtime dispatch defeats static reference counting); `is_special_method(name)`
  flags implicitly-dispatched names (Python `__dunder__`) as low-confidence orphans.
  Both default neutral on the base (False); Python overrides both; JS/Ruby/**TS**
  override the dynamic flag. **TS added beyond the legacy set** (it erases to JS at
  runtime — treating it as static while JS is dynamic would be incoherent). **Named
  `is_special_method`, not the work-list's `is_dunder`**: "dunder" is the Python token,
  not the cross-language concept (implicit runtime dispatch).

## Work-list (params-first order)

1. ✅ `extract_parameters` per grammar (the root).
2. `resolve_packages` overrides (Go/Java/Rust/C#) + Realm←module-root. **Reframed:**
   not a silent-deadening bug — `resolve_packages` already has a neutral per-dir default
   + isolated Python override, and the dep graph resolves edges by *module* name, not
   package. Gap is package *naming* (dir path vs declared identifier) everywhere + Java/C#
   *grouping* granularity (declared `package`/`namespace` vs directory). A fidelity
   enhancement; sequenced after the genuine de-overfit items.
3. ✅ `is_dynamic_language()` + `is_special_method()` facts — replaced the hardcoded
   `_DYNAMIC_LANGUAGES` set + `__x__` checks in `orphans`. TS added to the dynamic set;
   `is_dunder` renamed `is_special_method`. Suite 206→210.
4. ✅ Delegated the `__init__.py` literals in `scope/carve` + `graph/build` to
   `package_init_name()`. Python behavior preserved (martin-zones import resolution
   stays green); non-Python correctly skips the init branch. Suite 210→212.
5. ✅ C# grammar wheel loads (parse-level, not a fact); pinned by the all-grammar test.

### Status: the grammar-fact de-overfit pass is complete (#1, #3–#4).

The remaining shared-code Python assumptions are cleared. **#2 (`resolve_packages`)
stays open as a fidelity enhancement, not a de-overfit bug**, and **#5 (C# wheel) was a
packaging issue, not a grammar fact, and is resolved.** Every shared algorithm in
`metrics/` + `scope/carve` + `graph/build` now reads per-language idioms from grammar
facts; no `if lang ==` branch or hardcoded Python node-type/literal remains in them.