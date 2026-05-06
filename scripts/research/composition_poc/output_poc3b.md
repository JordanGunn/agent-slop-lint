# composition.first_parameter_drift — missing-receiver candidates

## Receiver candidate: `node`  (61 functions)

**Likely false positive** — not a class candidate

**Diagnosis**: This parameter is a third-party library type (e.g., tree-sitter AST node). Wrapping in a slop class would create an adapter layer with no clear benefit. Likely a coincidental cluster.

**Type annotations seen**: _(none — receiver is unannotated)_
**Files**: ccx.py, ck.py, halstead.py, npath.py

| Function | File | First param type |
|---|---|---|
| `_binary_op_text` | ccx.py | _(unannotated)_ |
| `_c_find_function_identifier` | ccx.py | _(unannotated)_ |
| `_c_name_extractor` | ccx.py | _(unannotated)_ |
| `_cpp_find_function_identifier` | ccx.py | _(unannotated)_ |
| `_cpp_is_destructor` | ccx.py | _(unannotated)_ |
| `_cpp_name_extractor` | ccx.py | _(unannotated)_ |
| `_default_is_function_node` | ccx.py | _(unannotated)_ |
| `_default_name_extractor` | ccx.py | _(unannotated)_ |
| `_extract_function_name` | ccx.py | _(unannotated)_ |
| `_julia_find_call` | ccx.py | _(unannotated)_ |
| `_julia_is_function_node` | ccx.py | _(unannotated)_ |
| `_julia_name_extractor` | ccx.py | _(unannotated)_ |
| `_node_text` | ccx.py | _(unannotated)_ |
| `_python_bool_op` | ccx.py | _(unannotated)_ |
| `_ruby_find_method_name` | ccx.py | _(unannotated)_ |
| `_ruby_is_function_node` | ccx.py | _(unannotated)_ |
| `_ruby_name_extractor` | ccx.py | _(unannotated)_ |
| `_collect_identifiers` | ck.py | _(unannotated)_ |
| `_extract_cpp_superclasses` | ck.py | _(unannotated)_ |
| `_extract_csharp_superclasses` | ck.py | _(unannotated)_ |
| `_extract_java_superclasses` | ck.py | _(unannotated)_ |
| `_extract_js_superclasses` | ck.py | _(unannotated)_ |
| `_extract_python_superclasses` | ck.py | _(unannotated)_ |
| `_extract_ruby_superclasses` | ck.py | _(unannotated)_ |
| `_extract_ts_superclasses` | ck.py | _(unannotated)_ |
| `_node_text` | ck.py | _(unannotated)_ |
| `_c_find_function_identifier` | halstead.py | _(unannotated)_ |
| `_c_name_extractor` | halstead.py | _(unannotated)_ |
| `_collect_tokens` | halstead.py | _(unannotated)_ |
| `_cpp_find_function_identifier` | halstead.py | _(unannotated)_ |
| `_cpp_is_destructor` | halstead.py | _(unannotated)_ |
| `_cpp_name_extractor` | halstead.py | _(unannotated)_ |
| `_default_is_function_node` | halstead.py | _(unannotated)_ |
| `_default_name_extractor` | halstead.py | _(unannotated)_ |
| `_extract_function_name` | halstead.py | _(unannotated)_ |
| `_julia_find_call` | halstead.py | _(unannotated)_ |
| `_julia_is_function_node` | halstead.py | _(unannotated)_ |
| `_julia_name_extractor` | halstead.py | _(unannotated)_ |
| `_node_text` | halstead.py | _(unannotated)_ |
| `_ruby_find_method_name` | halstead.py | _(unannotated)_ |
| `_ruby_is_function_node` | halstead.py | _(unannotated)_ |
| `_ruby_name_extractor` | halstead.py | _(unannotated)_ |
| `_c_find_function_identifier` | npath.py | _(unannotated)_ |
| `_c_name_extractor` | npath.py | _(unannotated)_ |
| `_cpp_find_function_identifier` | npath.py | _(unannotated)_ |
| `_cpp_is_destructor` | npath.py | _(unannotated)_ |
| `_cpp_name_extractor` | npath.py | _(unannotated)_ |
| `_default_is_function_node` | npath.py | _(unannotated)_ |
| `_default_name_extractor` | npath.py | _(unannotated)_ |
| `_extract_function_name` | npath.py | _(unannotated)_ |
| `_julia_find_call` | npath.py | _(unannotated)_ |
| `_julia_is_function_node` | npath.py | _(unannotated)_ |
| `_julia_name_extractor` | npath.py | _(unannotated)_ |
| `_node_text` | npath.py | _(unannotated)_ |
| `_npath_of_block` | npath.py | _(unannotated)_ |
| `_npath_of_flat_body` | npath.py | _(unannotated)_ |
| `_npath_of_if` | npath.py | _(unannotated)_ |
| `_npath_of_node` | npath.py | _(unannotated)_ |
| `_ruby_find_method_name` | npath.py | _(unannotated)_ |
| `_ruby_is_function_node` | npath.py | _(unannotated)_ |
| `_ruby_name_extractor` | npath.py | _(unannotated)_ |

## Receiver candidate: `root`  (8 functions)

**Weak candidate** — infrastructure parameter

**Diagnosis**: This parameter is infrastructure (filesystem path / scan root) rather than a domain entity. The cluster reflects shared configuration plumbing, not a missing class.

**Type annotations seen**: `Path`
**Files**: ccx.py, ck.py, halstead.py, npath.py

| Function | File | First param type |
|---|---|---|
| `_relative_path` | ccx.py | Path |
| `ccx_kernel` | ccx.py | Path |
| `_relative_path` | ck.py | Path |
| `ck_kernel` | ck.py | Path |
| `_relative_path` | halstead.py | Path |
| `halstead_kernel` | halstead.py | Path |
| `_relative_path` | npath.py | Path |
| `npath_kernel` | npath.py | Path |

## Receiver candidate: `file_path`  (5 functions)

**Weak candidate** — infrastructure parameter

**Diagnosis**: This parameter is infrastructure (filesystem path / scan root) rather than a domain entity. The cluster reflects shared configuration plumbing, not a missing class.

**Type annotations seen**: `Path`
**Files**: ccx.py, ck.py, halstead.py, npath.py

| Function | File | First param type |
|---|---|---|
| `_parse_file` | ccx.py | Path |
| `_walk_file` | ccx.py | Path |
| `_parse_file` | ck.py | Path |
| `_parse_file` | halstead.py | Path |
| `_parse_file` | npath.py | Path |

## Receiver candidate: `tree`  (5 functions)

**Likely false positive** — not a class candidate

**Diagnosis**: This parameter is a third-party library type (e.g., tree-sitter AST node). Wrapping in a slop class would create an adapter layer with no clear benefit. Likely a coincidental cluster.

**Type annotations seen**: _(none — receiver is unannotated)_
**Files**: ck.py

| Function | File | First param type |
|---|---|---|
| `_collect_body_classes` | ck.py | _(unannotated)_ |
| `_collect_cpp_outofline_methods` | ck.py | _(unannotated)_ |
| `_collect_go_classes` | ck.py | _(unannotated)_ |
| `_collect_ruby_classes` | ck.py | _(unannotated)_ |
| `_collect_rust_classes` | ck.py | _(unannotated)_ |

## Receiver candidate: `functions`  (3 functions)

**Strong candidate** — likely missing class

**Diagnosis**: `functions` is the natural receiver of these methods. Each function's body operates on `functions` as its primary subject. Folding them into a class with `functions` as `self` is the textbook conversion.

**Compositional mechanism**: a class taking `functions` as `self`. Each of the 3 functions becomes a method. The current shape (`fn(self, args)`) becomes `self.fn(args)`.

**Type annotations seen**: `list[FunctionMetrics]`
**Files**: ccx.py

| Function | File | First param type |
|---|---|---|
| `_aggregate_file_metrics` | ccx.py | list[FunctionMetrics] |
| `_build_guidance` | ccx.py | list[FunctionMetrics] |
| `_count_zones` | ccx.py | list[FunctionMetrics] |

