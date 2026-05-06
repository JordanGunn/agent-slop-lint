# composition.affix_polymorphism — missing-namespace candidates

## Candidate 1: missing namespace `language`

**Diagnosis**: an entity named `language` is implicit but unnamed in the codebase. The same alphabet of values appears as a varying token across multiple operations, with no shared abstraction binding the operations to the entity.

**Entity alphabet** (11 values): `c`, `cpp`, `csharp`, `default`, `java`, `js`, `julia`, `no`, `python`, `ruby`, `ts`

**Operations sharing this alphabet** (3):

- `*_name_extractor` — 5 entity values, 180 occurrences across 3 file(s)
- `*_is_function_node` — 3 entity values, 54 occurrences across 3 file(s)
- `extract_*_superclasses` — 8 entity values, 56 occurrences across 1 file(s)

**Compositional mechanisms that would make the entity explicit**:

- A `Language` class / trait / interface bundling per-entity data and behaviour. Each value of the alphabet becomes an instance or subclass; each operation becomes a method.
- A `Language` registry where each entity value maps to a record carrying its data and method references.
- A `language/` subpackage with one module per entity value, each implementing the operation set.

**Per-operation breakdown**:

| Operation | Entity value | Identifier | File |
|---|---|---|---|
| `*_name_extractor` | `c` | `_c_name_extractor` | ccx.py |
| `*_name_extractor` | `c` | `_c_name_extractor` | halstead.py |
| `*_name_extractor` | `c` | `_c_name_extractor` | npath.py |
| `*_name_extractor` | `cpp` | `_cpp_name_extractor` | ccx.py |
| `*_name_extractor` | `cpp` | `_cpp_name_extractor` | halstead.py |
| `*_name_extractor` | `cpp` | `_cpp_name_extractor` | npath.py |
| `*_name_extractor` | `default` | `_default_name_extractor` | ccx.py |
| `*_name_extractor` | `default` | `_default_name_extractor` | halstead.py |
| `*_name_extractor` | `default` | `_default_name_extractor` | npath.py |
| `*_name_extractor` | `julia` | `_julia_name_extractor` | ccx.py |
| `*_name_extractor` | `julia` | `_julia_name_extractor` | halstead.py |
| `*_name_extractor` | `julia` | `_julia_name_extractor` | npath.py |
| `*_name_extractor` | `ruby` | `_ruby_name_extractor` | ccx.py |
| `*_name_extractor` | `ruby` | `_ruby_name_extractor` | halstead.py |
| `*_name_extractor` | `ruby` | `_ruby_name_extractor` | npath.py |
| `*_is_function_node` | `default` | `_default_is_function_node` | ccx.py |
| `*_is_function_node` | `default` | `_default_is_function_node` | halstead.py |
| `*_is_function_node` | `default` | `_default_is_function_node` | npath.py |
| `*_is_function_node` | `julia` | `_julia_is_function_node` | ccx.py |
| `*_is_function_node` | `julia` | `_julia_is_function_node` | halstead.py |
| `*_is_function_node` | `julia` | `_julia_is_function_node` | npath.py |
| `*_is_function_node` | `ruby` | `_ruby_is_function_node` | ccx.py |
| `*_is_function_node` | `ruby` | `_ruby_is_function_node` | halstead.py |
| `*_is_function_node` | `ruby` | `_ruby_is_function_node` | npath.py |
| `extract_*_superclasses` | `cpp` | `_extract_cpp_superclasses` | ck.py |
| `extract_*_superclasses` | `csharp` | `_extract_csharp_superclasses` | ck.py |
| `extract_*_superclasses` | `java` | `_extract_java_superclasses` | ck.py |
| `extract_*_superclasses` | `js` | `_extract_js_superclasses` | ck.py |
| `extract_*_superclasses` | `no` | `_extract_no_superclasses` | ck.py |
| `extract_*_superclasses` | `python` | `_extract_python_superclasses` | ck.py |
| `extract_*_superclasses` | `ruby` | `_extract_ruby_superclasses` | ck.py |
| `extract_*_superclasses` | `ts` | `_extract_ts_superclasses` | ck.py |

## Candidate 2: missing namespace `<unnamed>`

**Diagnosis**: an entity named `<unnamed>` is implicit but unnamed in the codebase. The same alphabet of values appears as a varying token across multiple operations, with no shared abstraction binding the operations to the entity.

**Entity alphabet** (4 values): `cbo`, `dit`, `halstead`, `zone`

**Operations sharing this alphabet** (1):

- `compute_*` — 4 entity values, 12 occurrences across 3 file(s)

**Compositional mechanisms that would make the entity explicit**:

- A `<unnamed>` class / trait / interface bundling per-entity data and behaviour. Each value of the alphabet becomes an instance or subclass; each operation becomes a method.
- A `<unnamed>` registry where each entity value maps to a record carrying its data and method references.
- A `<unnamed>/` subpackage with one module per entity value, each implementing the operation set.

**Per-operation breakdown**:

| Operation | Entity value | Identifier | File |
|---|---|---|---|
| `compute_*` | `cbo` | `_compute_cbo` | ck.py |
| `compute_*` | `dit` | `_compute_dit` | ck.py |
| `compute_*` | `halstead` | `_compute_halstead` | halstead.py |
| `compute_*` | `zone` | `_compute_zone` | ccx.py |

## Candidate 3: missing namespace `<unnamed>`

**Diagnosis**: an entity named `<unnamed>` is implicit but unnamed in the codebase. The same alphabet of values appears as a varying token across multiple operations, with no shared abstraction binding the operations to the entity.

**Entity alphabet** (4 values): `ccx`, `ck`, `halstead`, `npath`

**Operations sharing this alphabet** (1):

- `*_kernel` — 4 entity values, 12 occurrences across 4 file(s)

**Compositional mechanisms that would make the entity explicit**:

- A `<unnamed>` class / trait / interface bundling per-entity data and behaviour. Each value of the alphabet becomes an instance or subclass; each operation becomes a method.
- A `<unnamed>` registry where each entity value maps to a record carrying its data and method references.
- A `<unnamed>/` subpackage with one module per entity value, each implementing the operation set.

**Per-operation breakdown**:

| Operation | Entity value | Identifier | File |
|---|---|---|---|
| `*_kernel` | `ccx` | `ccx_kernel` | ccx.py |
| `*_kernel` | `ck` | `ck_kernel` | ck.py |
| `*_kernel` | `halstead` | `halstead_kernel` | halstead.py |
| `*_kernel` | `npath` | `npath_kernel` | npath.py |

## Candidate 4: missing namespace `<unnamed>`

**Diagnosis**: an entity named `<unnamed>` is implicit but unnamed in the codebase. The same alphabet of values appears as a varying token across multiple operations, with no shared abstraction binding the operations to the entity.

**Entity alphabet** (4 values): `body`, `go`, `ruby`, `rust`

**Operations sharing this alphabet** (1):

- `collect_*_classes` — 4 entity values, 12 occurrences across 1 file(s)

**Compositional mechanisms that would make the entity explicit**:

- A `<unnamed>` class / trait / interface bundling per-entity data and behaviour. Each value of the alphabet becomes an instance or subclass; each operation becomes a method.
- A `<unnamed>` registry where each entity value maps to a record carrying its data and method references.
- A `<unnamed>/` subpackage with one module per entity value, each implementing the operation set.

**Per-operation breakdown**:

| Operation | Entity value | Identifier | File |
|---|---|---|---|
| `collect_*_classes` | `body` | `_collect_body_classes` | ck.py |
| `collect_*_classes` | `go` | `_collect_go_classes` | ck.py |
| `collect_*_classes` | `ruby` | `_collect_ruby_classes` | ck.py |
| `collect_*_classes` | `rust` | `_collect_rust_classes` | ck.py |

## Candidate 5: missing namespace `<unnamed>`

**Diagnosis**: an entity named `<unnamed>` is implicit but unnamed in the codebase. The same alphabet of values appears as a varying token across multiple operations, with no shared abstraction binding the operations to the entity.

**Entity alphabet** (3 values): `block`, `if`, `node`

**Operations sharing this alphabet** (1):

- `npath_of_*` — 3 entity values, 6 occurrences across 1 file(s)

**Compositional mechanisms that would make the entity explicit**:

- A `<unnamed>` class / trait / interface bundling per-entity data and behaviour. Each value of the alphabet becomes an instance or subclass; each operation becomes a method.
- A `<unnamed>` registry where each entity value maps to a record carrying its data and method references.
- A `<unnamed>/` subpackage with one module per entity value, each implementing the operation set.

**Per-operation breakdown**:

| Operation | Entity value | Identifier | File |
|---|---|---|---|
| `npath_of_*` | `block` | `_npath_of_block` | npath.py |
| `npath_of_*` | `if` | `_npath_of_if` | npath.py |
| `npath_of_*` | `node` | `_npath_of_node` | npath.py |

