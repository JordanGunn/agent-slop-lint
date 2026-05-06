# composition.formal_concept_lattice — structural decomposition

This report combines two views over the codebase:

1. **Section A** — formal concept analysis of the binary relation between candidate entities (languages) and candidate operations (the stem patterns). The lattice's concepts are the natural class groupings; the Hasse diagram is the inheritance graph.
2. **Section B** — kernel × language density matrix, showing where data and behaviour live across the (kernel, language) plane. A dense, uniform matrix indicates a two-dimensional structure that the current flat-file layout doesn't express.

## Section A — Formal Concept Lattice

### A.1 Binary relation: language × operation

Each ✓ marks a language having a per-language override for the given operation. The relation is the input to the lattice computation.

| Language | `aggregate_open_classes` | `bool_op` | `collect_classes` | `collect_outofline_methods` | `extract_embedded` | `extract_receiver_type` | `extract_superclasses` | `find_call` | `find_function_identifier` | `find_method_name` | `is_destructor` | `is_function_node` | `name_extractor` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `c` |  |  |  |  |  |  |  |  | ✓ |  |  |  | ✓ |
| `cpp` |  |  |  | ✓ |  |  | ✓ |  | ✓ |  | ✓ |  | ✓ |
| `csharp` |  |  |  |  |  |  | ✓ |  |  |  |  |  |  |
| `default` |  |  |  |  |  |  |  |  |  |  |  | ✓ | ✓ |
| `go` |  |  | ✓ |  | ✓ | ✓ |  |  |  |  |  |  |  |
| `java` |  |  |  |  |  |  | ✓ |  |  |  |  |  |  |
| `js` |  |  |  |  |  |  | ✓ |  |  |  |  |  |  |
| `julia` |  |  |  |  |  |  |  | ✓ |  |  |  | ✓ | ✓ |
| `python` |  | ✓ |  |  |  |  | ✓ |  |  |  |  |  |  |
| `ruby` | ✓ |  | ✓ |  |  |  | ✓ |  |  | ✓ |  | ✓ | ✓ |
| `rust` |  |  | ✓ |  |  |  |  |  |  |  |  |  |  |
| `ts` |  |  |  |  |  |  | ✓ |  |  |  |  |  |  |

**Entities (languages)**: 12
**Attributes (operations)**: 13
**Cells filled**: 28 / 156

### A.2 Formal concepts (13 total)

Each concept (E, I) is a pair where E is the maximal set of entities that share all operations in I, and I is the maximal set of operations shared by all entities in E. A concept with |E| ≥ 2 entities AND |I| ≥ 2 operations is a candidate **class**: the I operations would be methods on the class; the E entities would be instances or subclasses.

### Concept 0: BOTTOM
- entities: {}
- operations: {`aggregate_open_classes`, `bool_op`, `collect_classes`, `collect_outofline_methods`, `extract_embedded`, `extract_receiver_type`, `extract_superclasses`, `find_call`, `find_function_identifier`, `find_method_name`, `is_destructor`, `is_function_node`, `name_extractor`}

### Concept 1: {`ruby`} × {`aggregate_open_classes`, `collect_classes`, `extract_superclasses`, `find_method_name`, `is_function_node`, `name_extractor`}
- 1 entity: `ruby`
- 6 operations: `aggregate_open_classes`, `collect_classes`, `extract_superclasses`, `find_method_name`, `is_function_node`, `name_extractor`

### Concept 2: {`cpp`} × {`collect_outofline_methods`, `extract_superclasses`, `find_function_identifier`, `is_destructor`, `name_extractor`}
- 1 entity: `cpp`
- 5 operations: `collect_outofline_methods`, `extract_superclasses`, `find_function_identifier`, `is_destructor`, `name_extractor`

### Concept 3: {`go`} × {`collect_classes`, `extract_embedded`, `extract_receiver_type`}
- 1 entity: `go`
- 3 operations: `collect_classes`, `extract_embedded`, `extract_receiver_type`

### Concept 4: {`julia`} × {`find_call`, `is_function_node`, `name_extractor`}
- 1 entity: `julia`
- 3 operations: `find_call`, `is_function_node`, `name_extractor`

### Concept 5: {`default`, `julia`, `ruby`} × {`is_function_node`, `name_extractor`}
- 3 entities: `default`, `julia`, `ruby`
- 2 operations: `is_function_node`, `name_extractor`
- **Class candidate**: a `Language` (or named after the entity group) class providing these operations as methods. 3 entities would inherit from / instantiate this class.

### Concept 6: {`cpp`, `ruby`} × {`extract_superclasses`, `name_extractor`}
- 2 entities: `cpp`, `ruby`
- 2 operations: `extract_superclasses`, `name_extractor`
- **Class candidate**: a `Language` (or named after the entity group) class providing these operations as methods. 2 entities would inherit from / instantiate this class.

### Concept 7: {`c`, `cpp`} × {`find_function_identifier`, `name_extractor`}
- 2 entities: `c`, `cpp`
- 2 operations: `find_function_identifier`, `name_extractor`
- **Class candidate**: a `Language` (or named after the entity group) class providing these operations as methods. 2 entities would inherit from / instantiate this class.

### Concept 8: {`python`} × {`bool_op`, `extract_superclasses`}
- 1 entity: `python`
- 2 operations: `bool_op`, `extract_superclasses`

### Concept 9: {`cpp`, `csharp`, `java`, `js`, `python`, `ruby`, `ts`} × {`extract_superclasses`}
- 7 entities: `cpp`, `csharp`, `java`, `js`, `python`, `ruby`, `ts`
- 1 operation: `extract_superclasses`

### Concept 10: {`c`, `cpp`, `default`, `julia`, `ruby`} × {`name_extractor`}
- 5 entities: `c`, `cpp`, `default`, `julia`, `ruby`
- 1 operation: `name_extractor`

### Concept 11: {`go`, `ruby`, `rust`} × {`collect_classes`}
- 3 entities: `go`, `ruby`, `rust`
- 1 operation: `collect_classes`

### Concept 12: TOP
- entities: {`c`, `cpp`, `csharp`, `default`, `go`, `java`, `js`, `julia`, `python`, `ruby`, `rust`, `ts`}
- operations: {}

### A.3 Hasse diagram (immediate-subconcept edges)

Each edge `parent → child` means child's intent (operations) is an immediate strict superset of parent's. This is the **inheritance graph**: a child concept's class would extend its parent's.

- C1 ({ `aggregate_open_classes`, `collect_classes`, `extract_superclasses`, `find_method_name`, `is_function_node`, `name_extractor` }) → C0 ({ `aggregate_open_classes`, `bool_op`, `collect_classes`, `collect_outofline_methods`, `extract_embedded`, `extract_receiver_type`, `extract_superclasses`, `find_call`, `find_function_identifier`, `find_method_name`, `is_destructor`, `is_function_node`, `name_extractor` })  [entities {_(empty)_} extend entities {`ruby`}]
- C2 ({ `collect_outofline_methods`, `extract_superclasses`, `find_function_identifier`, `is_destructor`, `name_extractor` }) → C0 ({ `aggregate_open_classes`, `bool_op`, `collect_classes`, `collect_outofline_methods`, `extract_embedded`, `extract_receiver_type`, `extract_superclasses`, `find_call`, `find_function_identifier`, `find_method_name`, `is_destructor`, `is_function_node`, `name_extractor` })  [entities {_(empty)_} extend entities {`cpp`}]
- C3 ({ `collect_classes`, `extract_embedded`, `extract_receiver_type` }) → C0 ({ `aggregate_open_classes`, `bool_op`, `collect_classes`, `collect_outofline_methods`, `extract_embedded`, `extract_receiver_type`, `extract_superclasses`, `find_call`, `find_function_identifier`, `find_method_name`, `is_destructor`, `is_function_node`, `name_extractor` })  [entities {_(empty)_} extend entities {`go`}]
- C4 ({ `find_call`, `is_function_node`, `name_extractor` }) → C0 ({ `aggregate_open_classes`, `bool_op`, `collect_classes`, `collect_outofline_methods`, `extract_embedded`, `extract_receiver_type`, `extract_superclasses`, `find_call`, `find_function_identifier`, `find_method_name`, `is_destructor`, `is_function_node`, `name_extractor` })  [entities {_(empty)_} extend entities {`julia`}]
- C5 ({ `is_function_node`, `name_extractor` }) → C1 ({ `aggregate_open_classes`, `collect_classes`, `extract_superclasses`, `find_method_name`, `is_function_node`, `name_extractor` })  [entities {`ruby`} extend entities {`default`, `julia`, `ruby`}]
- C5 ({ `is_function_node`, `name_extractor` }) → C4 ({ `find_call`, `is_function_node`, `name_extractor` })  [entities {`julia`} extend entities {`default`, `julia`, `ruby`}]
- C6 ({ `extract_superclasses`, `name_extractor` }) → C1 ({ `aggregate_open_classes`, `collect_classes`, `extract_superclasses`, `find_method_name`, `is_function_node`, `name_extractor` })  [entities {`ruby`} extend entities {`cpp`, `ruby`}]
- C6 ({ `extract_superclasses`, `name_extractor` }) → C2 ({ `collect_outofline_methods`, `extract_superclasses`, `find_function_identifier`, `is_destructor`, `name_extractor` })  [entities {`cpp`} extend entities {`cpp`, `ruby`}]
- C7 ({ `find_function_identifier`, `name_extractor` }) → C2 ({ `collect_outofline_methods`, `extract_superclasses`, `find_function_identifier`, `is_destructor`, `name_extractor` })  [entities {`cpp`} extend entities {`c`, `cpp`}]
- C8 ({ `bool_op`, `extract_superclasses` }) → C0 ({ `aggregate_open_classes`, `bool_op`, `collect_classes`, `collect_outofline_methods`, `extract_embedded`, `extract_receiver_type`, `extract_superclasses`, `find_call`, `find_function_identifier`, `find_method_name`, `is_destructor`, `is_function_node`, `name_extractor` })  [entities {_(empty)_} extend entities {`python`}]
- C9 ({ `extract_superclasses` }) → C6 ({ `extract_superclasses`, `name_extractor` })  [entities {`cpp`, `ruby`} extend entities {`cpp`, `csharp`, `java`, `js`, `python`, `ruby`, `ts`}]
- C9 ({ `extract_superclasses` }) → C8 ({ `bool_op`, `extract_superclasses` })  [entities {`python`} extend entities {`cpp`, `csharp`, `java`, `js`, `python`, `ruby`, `ts`}]
- C10 ({ `name_extractor` }) → C5 ({ `is_function_node`, `name_extractor` })  [entities {`default`, `julia`, `ruby`} extend entities {`c`, `cpp`, `default`, `julia`, `ruby`}]
- C10 ({ `name_extractor` }) → C6 ({ `extract_superclasses`, `name_extractor` })  [entities {`cpp`, `ruby`} extend entities {`c`, `cpp`, `default`, `julia`, `ruby`}]
- C10 ({ `name_extractor` }) → C7 ({ `find_function_identifier`, `name_extractor` })  [entities {`c`, `cpp`} extend entities {`c`, `cpp`, `default`, `julia`, `ruby`}]
- C11 ({ `collect_classes` }) → C1 ({ `aggregate_open_classes`, `collect_classes`, `extract_superclasses`, `find_method_name`, `is_function_node`, `name_extractor` })  [entities {`ruby`} extend entities {`go`, `ruby`, `rust`}]
- C11 ({ `collect_classes` }) → C3 ({ `collect_classes`, `extract_embedded`, `extract_receiver_type` })  [entities {`go`} extend entities {`go`, `ruby`, `rust`}]
- C12 ({ _(empty)_ }) → C9 ({ `extract_superclasses` })  [entities {`cpp`, `csharp`, `java`, `js`, `python`, `ruby`, `ts`} extend entities {`c`, `cpp`, `csharp`, `default`, `go`, `java`, `js`, `julia`, `python`, `ruby`, `rust`, `ts`}]
- C12 ({ _(empty)_ }) → C10 ({ `name_extractor` })  [entities {`c`, `cpp`, `default`, `julia`, `ruby`} extend entities {`c`, `cpp`, `csharp`, `default`, `go`, `java`, `js`, `julia`, `python`, `ruby`, `rust`, `ts`}]
- C12 ({ _(empty)_ }) → C11 ({ `collect_classes` })  [entities {`go`, `ruby`, `rust`} extend entities {`c`, `cpp`, `csharp`, `default`, `go`, `java`, `js`, `julia`, `python`, `ruby`, `rust`, `ts`}]

### A.4 Direct inheritance candidates (entity-level)

Pairs of entities (parent, child) where the child's operation set is a strict superset of the parent's. These are the most actionable inheritance candidates: `class Child(Parent)` is structurally justified.

- `julia` inherits from `default`. `julia` overrides every operation `default` overrides, plus additional operations.
- `ruby` inherits from `default`. `ruby` overrides every operation `default` overrides, plus additional operations.
- `cpp` inherits from `c`. `cpp` overrides every operation `c` overrides, plus additional operations.


## Section B — Kernel × language density matrix

Each cell shows `d=N b=M` where d is data references (registry / config dict-key occurrences) and b is behaviour references (functions tagged with the language). A dot (·) means the cell is empty.

A dense, uniform matrix indicates a two-axis structure (kernel × language) currently flattened across files. The natural decomposition separates the two axes: per-language behaviour and data become a `Language` entity; per-kernel logic stays with the kernel.


| Language \ File | ccx.py | ck.py | halstead.py | npath.py | total |
|---|---|---|---|---|---|
| `c` | d=2 b=2 | · | d=2 b=2 | d=2 b=2 | d=6 b=6 |
| `cpp` | d=2 b=3 | d=4 b=2 | d=2 b=3 | d=2 b=3 | d=10 b=11 |
| `csharp` | d=2 b=0 | d=2 b=1 | d=2 b=0 | d=2 b=0 | d=8 b=1 |
| `default` | d=0 b=2 | · | d=0 b=2 | d=0 b=2 | d=0 b=6 |
| `go` | d=3 b=0 | d=2 b=3 | d=2 b=0 | d=2 b=0 | d=9 b=3 |
| `java` | d=2 b=0 | d=2 b=1 | d=2 b=0 | d=2 b=0 | d=8 b=1 |
| `javascript` | d=2 b=0 | d=2 b=0 | d=2 b=0 | d=2 b=0 | d=8 b=0 |
| `js` | · | d=0 b=1 | · | · | d=0 b=1 |
| `julia` | d=2 b=3 | · | d=2 b=3 | d=2 b=3 | d=6 b=9 |
| `python` | d=3 b=1 | d=2 b=1 | d=2 b=0 | d=2 b=0 | d=9 b=2 |
| `ruby` | d=2 b=3 | d=4 b=3 | d=2 b=3 | d=2 b=3 | d=10 b=12 |
| `rust` | d=2 b=0 | d=2 b=1 | d=2 b=0 | d=2 b=0 | d=8 b=1 |
| `ts` | · | d=0 b=1 | · | · | d=0 b=1 |
| `typescript` | d=2 b=0 | d=2 b=0 | d=2 b=0 | d=2 b=0 | d=8 b=0 |


## Section C — Diagnosis

The codebase has a 12-entity × 13-operation relation that forms a non-trivial concept lattice. The lattice contains 3 candidate classes (concepts with multiple entities sharing multiple operations) and 3 direct inheritance edges.

**Recommended decomposition**: a `Language` abstraction whose subclasses correspond to the lattice's join-irreducible concepts. The inheritance edges in section A.4 give the class hierarchy directly. Kernel-specific data (decision nodes, operator types, switch semantics) stays with the kernels — those fields are not part of the language axis.
