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
deadened **sentinels, hidden-mutators, imposters, slackers** and dropped every parameter
token from the lexicon on all non-Python code. The "not flagged ≠ clean" class.

Other Python assumptions found (work-list below): hardcoded `self`/`cls`, the profile
receiver-signal's `attribute`/`subscript` node types, `child_by_field_name("body")` in
clusters, the `{python,javascript,ruby}` dynamic-language set + `__x__` dunder checks,
and the `__init__.py` literals in `carve.py`/`graph/build.py`.

**Separate (not a language-agnosticism bug):** the C# grammar does not parse at all —
its tree-sitter wheel is not loading. Tracked apart; no grammar fact can help until it
parses.

## Grammar-fact contract

A grammar supplies (defaults in `base.py`, override where the language differs):

- `extract_parameters(node, content) -> ((name, annotation), ...)` — **done.** Base is
  now language-neutral: a parameter name is an identifier-typed node (the param node
  itself or its identifier children); types are distinct node kinds. Covers
  Python/Go/Rust/Java/TS/JS/Ruby. C/C++ override (`c_style_parameters` — names nest in
  declarators); Julia overrides (`julia_signature_parameters` — params under
  `signature → call_expression → argument_list`).
- `parameter_list_field()` / `parameter_name_node_types()` — tabular knobs for the base.
- `package_init_name()` — the package-marker filename (Python `__init__.py`; `None`
  where there is no init-file convention → runts is structurally N/A there).
- `resolve_packages(root, files)` — the language's package boundary (TODO: Go/Java/Rust).
- `receiver_parameter_names()` — names to exempt as implicit receivers (TODO).
- `member_access_patterns()` — node types for `recv.attr` / `recv[k]` (TODO).
- `body_field()` — the callable-body field name (exists; use it in clusters).
- `is_dunder(name)` / `is_dynamic_language()` — (TODO).

## Work-list (params-first order)

1. ✅ `extract_parameters` per grammar (the root).
2. `receiver_parameter_names()` — replace hardcoded `{self,cls}` in lexical view/clusters.
3. `member_access_patterns()` — rewrite `profile._receiver_call_count`.
4. `body_field()` + `noise_node_types()` delegation in clusters/profile.
5. `resolve_packages` overrides (Go/Java/Rust/C#) + Realm←module-root.
6. `is_dunder` / `is_dynamic_language` facts (orphans/relational).
7. Delegate the `__init__.py` literals in carve/graph to `package_init_name()`.
8. (separate) C# grammar wheel not loading — parse-level, not a fact.
