---
status: shipped
stability: first cut
ship_state: structural rules supported; CK metrics deferred
updated: 2026-04-26
---

# Julia support

Julia (`.jl`) is a first-class language for slop's structural rules.
Add it to your `.slop.toml` `languages` list or pass `--language julia`
on the CLI.

## What is supported

| Rule | Julia status | Notes |
|---|---|---|
| `complexity.cyclomatic` (McCabe CCX) | full | Counts `if`/`elseif`/`for`/`while`/`catch`/ternary plus `&&` / `||` short-circuits. |
| `complexity.cognitive` (Campbell CogC) | full | Same decision and nesting nodes; `elseif_clause` is treated as a compensating decision. |
| `complexity.weighted` (WMC) | n/a | WMC is a class metric; Julia uses multiple dispatch instead of methods-on-classes. See "What is not supported." |
| `complexity.npath` (Nejmeh NPATH) | partial | Counts top-level branches. Nested control flow inside `if`/`elseif`/`else` bodies is under-counted (Julia has no block-wrapper node, so the kernel currently flat-walks function bodies but does not recurse into clause bodies). Treat the number as a lower bound. |
| `halstead.volume` / `halstead.difficulty` | full | Operator and operand tables included for Julia keywords, infix operators, literal types. |
| `dependencies.cycles` | full | Tree-sitter queries cover `using Foo`, `using Foo, Bar`, `using Foo.Bar`, `using Foo: a, b`, `import Foo`, `import Base: show`. Module names are captured as raw strings; resolution to file paths is the same best-effort approach used for Python (matches by module-suffix to local files). |
| `architecture.distance` (I/A/D′) | yes, with caveat | Rides on `dependencies`. Abstractness uses `abstract_definition` as the abstract type marker. |
| `dead_code` (prune) | full | Definition queries cover `function_definition`, `struct_definition`, `abstract_definition`. |
| `hotspots` | full | Composes `complexity.cyclomatic` plus git churn; rides on the CCX layer. |
| `class.*` (Chidamber-Kemerer: CBO, DIT, NOC) | **deferred** | Julia has no classes. `struct` and `mutable struct` are data-only; methods live in dispatch tables, not on the type. CBO is computable in principle (count cross-struct references) but DIT and NOC don't translate. Same posture as Go and Rust (which also ship without these). |

## What is not supported (yet)

- **NPath nesting under `elseif`/`else` clauses** undercounts because Julia's grammar nests body statements directly inside the clause node rather than in a wrapping `block`. The kernel treats each `else_clause` as contributing one path; multi-branch nested control flow inside a clause is invisible.
- **CK class metrics** (see table above).
- **Typed-return short-form functions** (`f(x)::Int = x + 1`) are not yet detected. The full-form alternative `function f(x)::Int ... end` works correctly.

## Why CK metrics aren't shipped for Julia

Multiple dispatch is fundamentally different from method-receiver
dispatch. In Java or C#, a class owns its methods and inheritance forms
a tree — DIT and NOC are well-defined. In Julia, a method belongs to a
*function*, not a struct: `+(a::Int, b::Int)` is one method of `+`
specialised on `Int`. The `<:` relation between abstract types forms a
hierarchy but the methods that operate on that hierarchy are not
attached to any node in it. Reporting DIT or NOC over Julia struct
hierarchies would produce numbers that look like CK metrics but mean
something different. We follow the same posture as for Go (receiver
dispatch) and Rust (impl-based dispatch): ship CBO/WMC analogues only
when we have a precise mapping, otherwise skip.

## How language support is structured

Adding a language to slop is a tabular exercise. Each kernel that
touches tree-sitter has a per-language config:

- `_ast/treesitter.py` — `GRAMMAR_MAP` (language → tree-sitter package),
  `EXT_LANGUAGE_MAP` (extension → language).
- `_structural/ccx.py`, `_structural/npath.py`, `_structural/halstead.py`,
  `_structural/ck.py` — per-language `_LANG_CONFIG` dataclass listing the
  tree-sitter node types that count as functions, decisions, operators,
  etc., plus `_LANG_GLOBS` for the file-discovery glob.
- `_structural/deps.py` — `IMPORT_QUERIES` (tree-sitter queries) and
  `TEXT_IMPORT_REGEXES` (fallback) per language, plus an extension-to-
  language map in `_detect_file_language`.
- `_structural/robert.py` — `_LANG_GLOBS` (rides on `deps`).
- `_compose/usages.py` — `DEFINITION_QUERIES` per language (used by
  `prune` and `usages`).

Adding a new language means adding entries to those tables. The kernel
implementations are language-agnostic. Where a language's AST diverges
from the conventional `name`-field shape, slop uses the same Callable-
on-LangConfig pattern that `class_metrics`'s `extract_superclasses`
established: a `name_extractor` and `is_function_node` callable can be
registered on each kernel's per-language config. Julia uses both — its
short-form, operator-method, do-block, dotted-method-name, and where-
clause shapes all live in `_julia_name_extractor` and
`_julia_is_function_node` (defined in each of `ccx.py`, `npath.py`,
`halstead.py`).

## Calibrating thresholds for Julia

The shipped defaults — McCabe CCX zones at (10, 20, 50), NPath at 200,
Halstead Volume at 8000 — were calibrated on Python, JavaScript, and Go
corpora. They have not been re-calibrated against Julia. Expected
deviations:

- Julia code tends to use multi-branch dispatch (one short method per
  type combination) instead of one long branchy method, so per-function
  CCX should be *lower* than typical Python on the same problem. The
  defaults will under-flag Julia.
- NPath's documented under-counting compounds this for Julia. Treat any
  Julia NPath number as a lower bound.
- Halstead operand counts in Julia are inflated by the type-annotation
  syntax (`x::Int` produces `x` and `Int` as separate operands).

If you're using slop on a Julia codebase, expect to tighten thresholds
once you've seen the distribution. Run `slop lint --output json` and
look at the per-function values before settling on a threshold.

## Tree-sitter grammar pin

`tree-sitter-julia >= 0.21.0`, currently resolves to 0.23.1. Node
type names and S-expression query syntax may change between major
grammar versions. If queries start failing after a tree-sitter-julia
upgrade, the candidates are: `function_definition` shape, `if_statement`
clause structure, `selected_import` first-child anchor (used in
`deps.IMPORT_QUERIES["julia"]`).
