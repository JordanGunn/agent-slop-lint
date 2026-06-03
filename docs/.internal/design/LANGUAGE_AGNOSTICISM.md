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
  where there is no init-file convention → runts is structurally N/A there). **#40:**
  now also drives the package-init module qualname in `scope/carve` and the
  parent-package name spellings in `graph/build` — both previously hardcoded the
  `"__init__"`/`"__init__.py"` literal in shared code.
- `resolve_packages(root, files)` — the language's package boundary (TODO: Go/Java/Rust).
- `receiver_parameter_names()` — **not built; verified unnecessary.** The hardcoded
  `{self, cls}` is correct for Python and a *no-op* everywhere else: no other language
  puts its receiver in the parameter list (Go's is a separate `receiver` field, Rust's
  `&self` is a keyword node `extract_parameters` does not collect, Java/C++/C#/Ruby's
  receiver is implicit). Probed across all grammars. It is a uniform constant, not a
  language branch, so it does not violate the tabular rule — making it a grammar fact
  would be churn without a correctness change.
- `member_access_patterns()` — **done.** `(node_type, receiver_field)` pairs for
  `recv.attr` / `recv[k]`. The receiver-density signal previously read 0 on every
  non-Python language (`profile._receiver_call_count` hardcoded Python `attribute`/
  `subscript`), silently collapsing the first-param-cluster `missing_class` /
  `dispatch_family` classification. Each callable's grammar is threaded through
  `clusters._bodies_index` → `profile_cluster`. Verified non-zero on Go/Rust/Java.
  Node/field table below.
- `body_field()` — **done (delegated).** `clusters._body_roots(node, grammar)` resolves
  the walkable body language-agnostically: the named `body_field()` child where it is
  non-empty; else a `block_types()` wrapper child (Ruby's `body_statement`); else the
  flat-body direct children minus `body_skip_types()` (Julia). The old hardcoded
  `child_by_field_name("body")` silently dropped *every Julia callable* (its
  `function_definition` has no body field → `None`), leaving Julia's receiver-density
  signal dark. **Correction to the prior note:** Ruby was *not* actually dropped — its
  `method` node exposes a `body` field (→ `body_statement`), so the hardcode already
  reached it. Only Julia was genuinely dark.
- `noise_node_types()` — **not added; replaced by a universal property.** The
  Python-specific `_LEAF_OR_NOISE` set in `profile._signature_ngrams` (which listed
  `attribute`/`string`/`integer`/punctuation) leaked every other language's leaf tokens
  (`int_literal`, `:=`, `func`, `end`, `integer_literal`, …) into the structural ngram.
  Rather than enumerate each grammar's literal/keyword tokens (fragile: a new grammar
  silently leaks until someone remembers to list them), the signature now keeps **only
  interior nodes** (`node.child_count > 0`) — a node carries structural shape iff it has
  children; leaves are tokens. Zero per-grammar surface, no overfit. This deviates from
  the work-list's literal "`noise_node_types()` fact" wording but serves its goal more
  completely.
- `is_dynamic_language()` / `is_special_method(name)` — **done.** Replaced the
  hardcoded `_DYNAMIC_LANGUAGES = {python,javascript,ruby}` set and the `__x__` dunder
  checks that were buried in shared `orphans._confidence` and `relational._meaningful`.
  `is_dynamic_language()` lowers orphan confidence one tick (runtime dispatch defeats
  static reference counting); `is_special_method(name)` flags implicitly-dispatched
  names (Python `__dunder__`) as low-confidence orphans and non-meaningful callees.
  Both default neutral on the base (False); Python overrides both, JS/Ruby/**TS**
  override the dynamic flag. **TS added beyond the legacy set** (it erases to JS at
  runtime — treating it as static while JS is dynamic would be incoherent). **Named
  `is_special_method`, not the work-list's `is_dunder`**: "dunder" is the Python token,
  not the cross-language concept (implicit runtime dispatch).

## Work-list (params-first order)

1. ✅ `extract_parameters` per grammar (the root).
2. ~~`receiver_parameter_names()`~~ — **dropped: verified no-op** (see contract above).
   `{self, cls}` is correct for Python, harmless everywhere else.
3. ✅ `member_access_patterns()` — `profile._receiver_call_count` now iterates the
   grammar's patterns; signal verified live on Go/Rust/Java (was dark).
4. ✅ `body_field()` delegation via `clusters._body_roots` (field → block wrapper →
   flat-children); `noise_node_types()` superseded by the interior-only ngram rule.
   Unblocks the receiver signal on **Julia** (the one genuinely flat-body language —
   was dropped; now `mean_receiver_calls=2.0`/`missing_class`, verified). Ruby already
   worked via its `body` field. Suite 204→206.
5. `resolve_packages` overrides (Go/Java/Rust/C#) + Realm←module-root. **Reframed:**
   not a silent-deadening bug — `resolve_packages` already has a neutral per-dir default
   + isolated Python override, and the dep graph resolves edges by *module* name, not
   package. Gap is package *naming* (dir path vs declared identifier) everywhere + Java/C#
   *grouping* granularity (declared `package`/`namespace` vs directory). A fidelity
   enhancement; sequenced after the genuine de-overfit items.
6. ✅ `is_dynamic_language()` + `is_special_method()` facts — replaced the hardcoded
   `_DYNAMIC_LANGUAGES` set + `__x__` checks in `orphans`/`relational`. TS added to the
   dynamic set; `is_dunder` renamed `is_special_method`. Suite 206→210.
7. ✅ Delegated the `__init__.py` literals in `scope/carve` + `graph/build` to
   `package_init_name()`. Python behavior preserved (martin-zones import resolution
   stays green); non-Python correctly skips the init branch. Suite 210→212.
8. (separate) C# grammar wheel not loading — parse-level, not a fact.

### Status: the grammar-fact de-overfit pass is complete (#1, #3–#4, #6–#7).

The remaining shared-code Python assumptions are cleared. **#5 (`resolve_packages`)
stays open as a fidelity enhancement, not a de-overfit bug** (reframed above), and **#8
(C# wheel) is a packaging issue, not a grammar fact.** Every shared algorithm in
`metrics/` + `scope/carve` + `graph/build` now reads per-language idioms from grammar
facts; no `if lang ==` branch or hardcoded Python node-type/literal remains in them.

### Verified member-access node/field table (#36)

| Grammar | `member_access_patterns()` |
|---|---|
| python | `(attribute,object)` `(subscript,value)` |
| go | `(selector_expression,operand)` `(index_expression,operand)` |
| rust / julia | `(field_expression,value)` |
| java | `(field_access,object)` `(array_access,array)` |
| c / cpp | `(field_expression,argument)` `(subscript_expression,argument)` |
| javascript / typescript | `(member_expression,object)` `(subscript_expression,object)` |
| ruby | `(call,receiver)` `(element_reference,object)` |
| c_sharp | `(member_access_expression,expression)` `(element_access_expression,expression)` — **unverified** (wheel does not parse) |
