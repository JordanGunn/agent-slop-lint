# PoC 1 — Token-Levenshtein affix-polymorphism candidates

## Pattern: `*_name_extractor` (varying position 0)

**Type alphabet** (5 values): `c`, `cpp`, `default`, `julia`, `ruby`
**Total members**: 180

| Varying token | Identifiers |
|---|---|
| `c` | `_c_name_extractor` (ccx.py), `_c_name_extractor` (halstead.py), `_c_name_extractor` (npath.py) |
| `cpp` | `_cpp_name_extractor` (ccx.py), `_cpp_name_extractor` (halstead.py), `_cpp_name_extractor` (npath.py) |
| `default` | `_default_name_extractor` (ccx.py), `_default_name_extractor` (halstead.py), `_default_name_extractor` (npath.py) |
| `julia` | `_julia_name_extractor` (ccx.py), `_julia_name_extractor` (halstead.py), `_julia_name_extractor` (npath.py) |
| `ruby` | `_ruby_name_extractor` (ccx.py), `_ruby_name_extractor` (halstead.py), `_ruby_name_extractor` (npath.py) |

## Pattern: `extract_*_superclasses` (varying position 1)

**Type alphabet** (8 values): `cpp`, `csharp`, `java`, `js`, `no`, `python`, `ruby`, `ts`
**Total members**: 56

| Varying token | Identifiers |
|---|---|
| `cpp` | `_extract_cpp_superclasses` (ck.py) |
| `csharp` | `_extract_csharp_superclasses` (ck.py) |
| `java` | `_extract_java_superclasses` (ck.py) |
| `js` | `_extract_js_superclasses` (ck.py) |
| `no` | `_extract_no_superclasses` (ck.py) |
| `python` | `_extract_python_superclasses` (ck.py) |
| `ruby` | `_extract_ruby_superclasses` (ck.py) |
| `ts` | `_extract_ts_superclasses` (ck.py) |

## Pattern: `*_is_function_node` (varying position 0)

**Type alphabet** (3 values): `default`, `julia`, `ruby`
**Total members**: 54

| Varying token | Identifiers |
|---|---|
| `default` | `_default_is_function_node` (ccx.py), `_default_is_function_node` (halstead.py), `_default_is_function_node` (npath.py) |
| `julia` | `_julia_is_function_node` (ccx.py), `_julia_is_function_node` (halstead.py), `_julia_is_function_node` (npath.py) |
| `ruby` | `_ruby_is_function_node` (ccx.py), `_ruby_is_function_node` (halstead.py), `_ruby_is_function_node` (npath.py) |

## Pattern: `compute_*` (varying position 1)

**Type alphabet** (4 values): `cbo`, `dit`, `halstead`, `zone`
**Total members**: 12

| Varying token | Identifiers |
|---|---|
| `cbo` | `_compute_cbo` (ck.py) |
| `dit` | `_compute_dit` (ck.py) |
| `halstead` | `_compute_halstead` (halstead.py) |
| `zone` | `_compute_zone` (ccx.py) |

## Pattern: `*_kernel` (varying position 0)

**Type alphabet** (4 values): `ccx`, `ck`, `halstead`, `npath`
**Total members**: 12

| Varying token | Identifiers |
|---|---|
| `ccx` | `ccx_kernel` (ccx.py) |
| `ck` | `ck_kernel` (ck.py) |
| `halstead` | `halstead_kernel` (halstead.py) |
| `npath` | `npath_kernel` (npath.py) |

## Pattern: `collect_*_classes` (varying position 1)

**Type alphabet** (4 values): `body`, `go`, `ruby`, `rust`
**Total members**: 12

| Varying token | Identifiers |
|---|---|
| `body` | `_collect_body_classes` (ck.py) |
| `go` | `_collect_go_classes` (ck.py) |
| `ruby` | `_collect_ruby_classes` (ck.py) |
| `rust` | `_collect_rust_classes` (ck.py) |

## Pattern: `npath_of_*` (varying position 2)

**Type alphabet** (3 values): `block`, `if`, `node`
**Total members**: 6

| Varying token | Identifiers |
|---|---|
| `block` | `_npath_of_block` (npath.py) |
| `if` | `_npath_of_if` (npath.py) |
| `node` | `_npath_of_node` (npath.py) |

