# Language interface + concrete grammars

Status: Language hierarchy and the set of concrete grammars
are locked. The `Language.parse(path)` return type is the
remaining open item and is tied to the record shapes
discussed in `codebase.md`.

Companion docs: `codebase.md` covers the corpus orchestrator
that consumes grammars; `linter.md` covers the run loop that
sits above Codebase.

## Scope of this document

What is settled:

- The abstract `Language` interface and its paradigm extensions.
- The set of concrete grammar classes (one per supported
  language) and which paradigm each inherits.
- The fully-spelled naming convention for those classes.
- The principle: `Language` is a pure abstract interface; the
  concrete language classes ARE the grammar implementations
  (no separate `Grammar` object held by `Language`).

What is NOT settled and is left for follow-up:

- What `Language.parse(path)` returns (tied to record shapes
  in `codebase.md`).
- Grammar registration mechanism (constructor injection vs.
  default registry vs. hybrid — leaning hybrid; tied to the
  Codebase API decision).

---

## Locked: Language as a pure abstract interface

`Language` is the base grammar contract — the interface every
concrete grammar implementation satisfies. It is abstract; it
cannot be instantiated. The paradigm subclasses (`ObjectOriented`,
`Procedural`, `MultiPurpose`) are also abstract — they extend the
contract with capability methods specific to the paradigm but do
not provide implementations.

The named concrete classes (`Python`, `Java`, etc.) are the
grammar implementations. Each ONE inherits from the appropriate
paradigm interface and provides the per-language realization of
the contract: tree-sitter dispatch, node-type tables, name
extraction quirks, body extraction, first-parameter extraction.

This collapses the prior proposal of "a `Language` *has-a*
`Grammar`" into a single concrete layer. There is no separate
`Grammar` class; the concrete language class IS the grammar.
Parser-substrate flexibility (tree-sitter vs. text scanning,
which `_structural/deps.py` and `_structural/out_parameters.py`
already need for some queries) becomes an internal implementation
choice of each grammar, not an architectural axis.

### Hierarchy

```
Language(ABC)                         # base grammar interface
├── ObjectOriented(Language)          # adds class/method capabilities
├── Procedural(Language)              # adds free-function capability
└── MultiPurpose(ObjectOriented, Procedural)
                                      # named diamond — multi-paradigm marker
```

`ObjectOriented` is the marker for any language whose grammar
emits **named scopes containing methods with implicit receivers**.
This includes Java, Python, C++, Ruby, Go (struct + receiver
methods), and Rust (impl blocks) — all four pillars need not
apply (Rust lacks inheritance; the criterion is the receiver-
binding semantic, not the full OOP suite).

`Procedural` is the marker for any language whose grammar emits
**free functions** — callables with no implicit receiver and no
enclosing class scope.

`MultiPurpose` is a named diamond. As a marker type it has no
method body day one, but it does real work: kernels asking "is
this a multi-paradigm language?" can write
`isinstance(grammar, MultiPurpose)` instead of
`isinstance(grammar, ObjectOriented) and isinstance(grammar, Procedural)`.
Future behavior unique to multi-paradigm languages would land
here.

### Concrete grammars

| Grammar      | Inherits         | Notes                                    |
|--------------|------------------|------------------------------------------|
| `Python`     | `MultiPurpose`   |                                          |
| `Java`       | `ObjectOriented` | No free functions (`static` lives in a class) |
| `Cpp`        | `MultiPurpose`   |                                          |
| `C`          | `Procedural`     | No classes                               |
| `Go`         | `MultiPurpose`   | Struct + receiver-bound methods          |
| `Rust`       | `MultiPurpose`   | Inheritance gaps raise `NotImplementedError` until a rule needs them |
| `JavaScript` | `MultiPurpose`   |                                          |
| `TypeScript` | `MultiPurpose`   |                                          |
| `Ruby`       | `MultiPurpose`   |                                          |
| `Julia`      | `Procedural`     | Multimethods don't bind receivers        |
| `CSharp`     | `ObjectOriented` |                                          |

### Naming convention

- `Cpp` and `C` stay short — unambiguous in context.
- `JavaScript`, `TypeScript`, `CSharp` use the full spelling —
  the abbreviated forms (`Js`, `Ts`, `Cs`) are too ambiguous
  for grep and read poorly in `isinstance` checks.
- The class name is the language name, not `*Grammar` or
  `*Language` suffixed. The IS-A relationship is encoded in the
  inheritance, not in the name suffix. `class Python(MultiPurpose)`
  is the grammar implementation for Python; the file location
  and the inheritance chain make this unambiguous.

### Kernel-side polymorphism

Kernels never branch on language identity (`if lang.name == "java"`).
They narrow on the paradigm interface they need:

```python
def some_kernel(grammars: Iterable[Language]):
    for g in grammars:
        if isinstance(g, Procedural):
            ...   # depends only on free-function methods
        if isinstance(g, ObjectOriented):
            ...   # depends only on class/method methods
```

This is consistent with the existing tabular-dispatch principle:
shared code dispatches by capability, never by language identity.
The mechanism upgrades from "Callable field on a config dataclass"
to "method on a concrete grammar class," but the principle is
unchanged — and the type system now enforces it at the boundary
via the abstract interfaces.

---

## Open — next rounds

### `Language.parse(path)` return type

Tree-shaped (returns a root `Scope` with nested children) vs.
flat (returns parallel lists of `Scope` and `Callable` records,
linked by qualname). Hybrid (both views materialised in one
pass) was sketched but not stress-tested against kernel needs.

This is tied to the record-shape round in `codebase.md` — what
a grammar contracts to return depends on what records the
records-round settles on.

### Grammar registration

Three options sketched:

1. Explicit constructor injection: `Codebase.scan(root, grammars=[Python(), Go()])`.
2. Default registry: built-in `GRAMMARS` dict, picked by file extension.
3. Hybrid: (1) with a default-supplied registry when the caller
   omits `grammars=`.

Inclined toward (3) but tied to the `Codebase.scan()` API
decision in `codebase.md`.

---

## Why Language locked first

Every downstream shape (records, Codebase, view APIs) reads
off what grammars actually contract to produce. Locking the
Language interface first means the next rounds can stress-
test specifics against a stable abstract surface; locking
everything together would invite cross-cutting churn the
moment any one piece needed adjustment.
