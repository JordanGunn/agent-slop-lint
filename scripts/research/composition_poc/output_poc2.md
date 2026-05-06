# PoC 2 — Agglomerative Jaccard clustering candidates

## Cluster 1 (18 members)

**Shared tokens**: `name`, `node`

| Function | File | All tokens |
|---|---|---|
| `_default_name_extractor` | ccx.py | default, extractor, name, node |
| `_julia_name_extractor` | ccx.py | extractor, julia, name, node |
| `_c_name_extractor` | ccx.py | c, extractor, name, node |
| `_cpp_name_extractor` | ccx.py | cpp, extractor, name, node |
| `_ruby_find_method_name` | ccx.py | find, method, name, node, ruby |
| `_ruby_name_extractor` | ccx.py | extractor, name, node, ruby |
| `_default_name_extractor` | npath.py | default, extractor, name, node |
| `_julia_name_extractor` | npath.py | extractor, julia, name, node |
| `_c_name_extractor` | npath.py | c, extractor, name, node |
| `_cpp_name_extractor` | npath.py | cpp, extractor, name, node |
| `_ruby_find_method_name` | npath.py | find, method, name, node, ruby |
| `_ruby_name_extractor` | npath.py | extractor, name, node, ruby |
| `_default_name_extractor` | halstead.py | default, extractor, name, node |
| `_julia_name_extractor` | halstead.py | extractor, julia, name, node |
| `_c_name_extractor` | halstead.py | c, extractor, name, node |
| `_cpp_name_extractor` | halstead.py | cpp, extractor, name, node |
| `_ruby_find_method_name` | halstead.py | find, method, name, node, ruby |
| `_ruby_name_extractor` | halstead.py | extractor, name, node, ruby |

## Cluster 2 (9 members)

**Shared tokens**: `function`, `is`, `node`

| Function | File | All tokens |
|---|---|---|
| `_default_is_function_node` | ccx.py | default, function, is, node |
| `_julia_is_function_node` | ccx.py | function, is, julia, node |
| `_ruby_is_function_node` | ccx.py | function, is, node, ruby |
| `_default_is_function_node` | npath.py | default, function, is, node |
| `_julia_is_function_node` | npath.py | function, is, julia, node |
| `_ruby_is_function_node` | npath.py | function, is, node, ruby |
| `_default_is_function_node` | halstead.py | default, function, is, node |
| `_julia_is_function_node` | halstead.py | function, is, julia, node |
| `_ruby_is_function_node` | halstead.py | function, is, node, ruby |

## Cluster 3 (8 members)

**Shared tokens**: `extract`, `node`, `superclasses`

| Function | File | All tokens |
|---|---|---|
| `_extract_python_superclasses` | ck.py | extract, node, python, superclasses |
| `_extract_csharp_superclasses` | ck.py | csharp, extract, node, superclasses |
| `_extract_java_superclasses` | ck.py | extract, java, node, superclasses |
| `_extract_ts_superclasses` | ck.py | extract, node, superclasses, ts |
| `_extract_js_superclasses` | ck.py | extract, js, node, superclasses |
| `_extract_cpp_superclasses` | ck.py | cpp, extract, node, superclasses |
| `_extract_ruby_superclasses` | ck.py | extract, node, ruby, superclasses |
| `_extract_no_superclasses` | ck.py | extract, no, node, superclasses |

## Cluster 4 (6 members)

**Shared tokens**: `find`, `function`, `identifier`, `node`

| Function | File | All tokens |
|---|---|---|
| `_c_find_function_identifier` | ccx.py | c, find, function, identifier, node |
| `_cpp_find_function_identifier` | ccx.py | cpp, find, function, identifier, node |
| `_c_find_function_identifier` | npath.py | c, find, function, identifier, node |
| `_cpp_find_function_identifier` | npath.py | cpp, find, function, identifier, node |
| `_c_find_function_identifier` | halstead.py | c, find, function, identifier, node |
| `_cpp_find_function_identifier` | halstead.py | cpp, find, function, identifier, node |

## Cluster 5 (5 members)

**Shared tokens**: `file`, `path`

| Function | File | All tokens |
|---|---|---|
| `_parse_file` | ccx.py | file, parse, path |
| `_walk_file` | ccx.py | file, path, walk |
| `_parse_file` | npath.py | file, parse, path |
| `_parse_file` | halstead.py | file, parse, path |
| `_parse_file` | ck.py | file, parse, path |

## Cluster 6 (5 members)

**Shared tokens**: `node`, `text`

| Function | File | All tokens |
|---|---|---|
| `_node_text` | ccx.py | node, text |
| `_binary_op_text` | ccx.py | binary, node, op, text |
| `_node_text` | npath.py | node, text |
| `_node_text` | halstead.py | node, text |
| `_node_text` | ck.py | node, text |

## Cluster 7 (4 members)

**Shared tokens**: `kernel`, `root`

| Function | File | All tokens |
|---|---|---|
| `ccx_kernel` | ccx.py | ccx, kernel, root |
| `npath_kernel` | npath.py | kernel, npath, root |
| `halstead_kernel` | halstead.py | halstead, kernel, root |
| `ck_kernel` | ck.py | ck, kernel, root |

## Cluster 8 (4 members)

**Shared tokens**: `path`, `relative`, `root`

| Function | File | All tokens |
|---|---|---|
| `_relative_path` | ccx.py | path, relative, root |
| `_relative_path` | npath.py | path, relative, root |
| `_relative_path` | halstead.py | path, relative, root |
| `_relative_path` | ck.py | path, relative, root |

## Cluster 9 (4 members)

**Shared tokens**: `node`, `npath`, `of`

| Function | File | All tokens |
|---|---|---|
| `_npath_of_flat_body` | npath.py | body, flat, node, npath, of |
| `_npath_of_block` | npath.py | block, node, npath, of |
| `_npath_of_node` | npath.py | node, npath, of |
| `_npath_of_if` | npath.py | if, node, npath, of |

## Cluster 10 (4 members)

**Shared tokens**: `classes`, `collect`, `tree`

| Function | File | All tokens |
|---|---|---|
| `_collect_ruby_classes` | ck.py | classes, collect, ruby, tree |
| `_collect_body_classes` | ck.py | body, classes, collect, tree |
| `_collect_go_classes` | ck.py | classes, collect, go, tree |
| `_collect_rust_classes` | ck.py | classes, collect, rust, tree |

## Cluster 11 (3 members)

**Shared tokens**: `call`, `find`, `julia`, `node`

| Function | File | All tokens |
|---|---|---|
| `_julia_find_call` | ccx.py | call, find, julia, node |
| `_julia_find_call` | npath.py | call, find, julia, node |
| `_julia_find_call` | halstead.py | call, find, julia, node |

## Cluster 12 (3 members)

**Shared tokens**: `cpp`, `destructor`, `is`, `node`

| Function | File | All tokens |
|---|---|---|
| `_cpp_is_destructor` | ccx.py | cpp, destructor, is, node |
| `_cpp_is_destructor` | npath.py | cpp, destructor, is, node |
| `_cpp_is_destructor` | halstead.py | cpp, destructor, is, node |

## Cluster 13 (3 members)

**Shared tokens**: `extract`, `function`, `name`, `node`

| Function | File | All tokens |
|---|---|---|
| `_extract_function_name` | ccx.py | extract, function, name, node |
| `_extract_function_name` | npath.py | extract, function, name, node |
| `_extract_function_name` | halstead.py | extract, function, name, node |

