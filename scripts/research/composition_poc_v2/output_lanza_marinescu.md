# PoC v2.7 — Lanza/Marinescu-style detection strategy

Root: `cli/slop`  |  Files: 70

## Detection rule

```
ExtractClassCandidate(module) =
    (function_count ≥ 5)
    AND (cluster_count ≥ 2)
    AND (each cluster size ≥ 3)
```

| File | # Functions | # Clusters (size ≥ 3) | Strong-cluster receivers | Verdict |
|---|---|---|---|---|
| `_ast/query.py` | 5 | 0 | — | — |
| `_compat.py` | 12 | 1 | `raw_rules` | — |
| `_compose/git.py` | 7 | 1 | `cwd` | — |
| `_compose/hotspots.py` | 11 | 0 | — | — |
| `_compose/prune.py` | 7 | 0 | — | — |
| `_lexical/_naming.py` | 5 | 1 | — | — |
| `_lexical/boilerplate_docstrings.py` | 5 | 0 | — | — |
| `_lexical/identifier_singletons.py` | 8 | 2 | `ctx` | **candidate** |
| `_lexical/identifier_tokens.py` | 6 | 1 | — | — |
| `_lexical/stutter.py` | 6 | 0 | — | — |
| `_structural/ccx.py` | 30 | 2 | `functions` | **candidate** |
| `_structural/ck.py` | 30 | 2 | — | **candidate** |
| `_structural/clone_density.py` | 7 | 1 | — | — |
| `_structural/composition.py` | 19 | 0 | — | — |
| `_structural/deps.py` | 27 | 3 | `file_paths` | **candidate** |
| `_structural/halstead.py` | 22 | 1 | — | — |
| `_structural/local_imports.py` | 8 | 1 | — | — |
| `_structural/npath.py` | 24 | 1 | — | — |
| `_structural/out_parameters.py` | 22 | 3 | `fn_node`, `body_node` | **candidate** |
| `_structural/robert.py` | 19 | 1 | `pkg_files` | — |
| `_structural/sibling_calls.py` | 14 | 3 | `body` | **candidate** |
| `_structural/stringly_typed.py` | 15 | 2 | `fn_node` | **candidate** |
| `cli.py` | 15 | 1 | `args` | — |
| `color.py` | 8 | 1 | `text` | — |
| `config.py` | 13 | 1 | `raw` | — |
| `engine.py` | 15 | 1 | `violation` | — |
| `output.py` | 17 | 3 | `rule_name`, `result`, `rule_pairs` | **candidate** |
| `rules/stutter.py` | 5 | 1 | — | — |

## Candidates: 8 file(s)

### `_lexical/identifier_singletons.py` (8 functions)

- `node` (4 members, weak/false-positive): `walk`, `_record_targets`, `walk`, `walk`
- `ctx` (3 members, STRONG): `_collect_python_bindings`, `_count_uses`, `_collect_returns`

_Reading: one strong-receiver cluster (`ctx`) plus other smaller clusters. The single strong cluster is the primary extraction candidate._

### `_structural/ccx.py` (30 functions)

- `node` (19 members, weak/false-positive): `_default_name_extractor`, `_default_is_function_node`, `_julia_find_call`, `_julia_name_extractor`, `_julia_is_function_node` (+14)
- `functions` (3 members, STRONG): `_aggregate_file_metrics`, `_build_guidance`, `_count_zones`

_Reading: one strong-receiver cluster (`functions`) plus other smaller clusters. The single strong cluster is the primary extraction candidate._

### `_structural/ck.py` (30 functions)

- `node` (14 members, weak/false-positive): `_node_text`, `_extract_python_superclasses`, `_extract_csharp_superclasses`, `_extract_java_superclasses`, `_extract_ts_superclasses` (+9)
- `tree` (5 members, weak/false-positive): `_collect_cpp_outofline_methods`, `_collect_ruby_classes`, `_collect_body_classes`, `_collect_go_classes`, `_collect_rust_classes`

_Reading: multiple clusters but none classified strong. File may be a god-module without a clean class hiding inside._

### `_structural/deps.py` (27 functions)

- `root` (6 members, weak/false-positive): `deps_kernel`, `_discover_dependency_files`, `_build_dependency_graph`, `_build_module_index`, `_module_names_for_path` (+1)
- `file_paths` (4 members, STRONG): `_resolve_edges`, `_reverse_adjacency`, `_build_file_deps`, `_extract_all_imports`
- `fp` (4 members, weak/false-positive): `_extract_imports_ast`, `_extract_imports_text`, `_extract_go_imports_text`, `_detect_file_language`

_Reading: one strong-receiver cluster (`file_paths`) plus other smaller clusters. The single strong cluster is the primary extraction candidate._

### `_structural/out_parameters.py` (22 functions)

- `fn_node` (8 members, STRONG): `_process_python_function`, `_extract_python_params`, `_process_c_function`, `_c_fn_name`, `_c_extract_pointer_params` (+3)
- `fp` (6 members, weak/false-positive): `_scan_python`, `_count_functions_python`, `_scan_js_text`, `_scan_go_text`, `_scan_c` (+1)
- `body_node` (3 members, STRONG): `_find_python_mutations`, `_c_find_mutations`, `_cpp_find_mutations`

_Reading: this file has 2 distinct strong-receiver clusters. Lanza/Marinescu's interpretation is that such a file is doing the work of multiple cohesive units; splitting along the receiver boundaries is the canonical Extract Class move._

### `_structural/sibling_calls.py` (14 functions)

- `node` (4 members, weak/false-positive): `_fn_name_from_node`, `_c_function_name`, `_cpp_function_name`, `_ruby_function_name`
- `body` (4 members, STRONG): `_gather_callees`, `_gather_callees_c`, `_gather_callees_cpp`, `_gather_callees_ruby`
- `fp` (4 members, weak/false-positive): `_analyze_python_file`, `_analyze_c_file`, `_analyze_cpp_file`, `_analyze_ruby_file`

_Reading: one strong-receiver cluster (`body`) plus other smaller clusters. The single strong cluster is the primary extraction candidate._

### `_structural/stringly_typed.py` (15 functions)

- `fp` (5 members, weak/false-positive): `_scan_python_file`, `_count_python_functions`, `_scan_c_file`, `_scan_cpp_file`, `_scan_ruby_file`
- `fn_node` (5 members, STRONG): `_process_python_function`, `_process_c_function`, `_c_fn_name`, `_process_cpp_function`, `_cpp_fn_name_local`

_Reading: one strong-receiver cluster (`fn_node`) plus other smaller clusters. The single strong cluster is the primary extraction candidate._

### `output.py` (17 functions)

- `result` (5 members, STRONG): `format_human`, `_group_by_category`, `_format_footer`, `format_quiet`, `format_json`
- `rule_pairs` (5 members, STRONG): `_render_category_findings`, `_rules_with_violations`, `_rules_with_waivers`, `_aggregate_category`, `_category_header_extras`
- `rule_name` (4 members, STRONG): `_category_for`, `_short_name_for`, `_render_violations`, `_render_waived`

_Reading: this file has 3 distinct strong-receiver clusters. Lanza/Marinescu's interpretation is that such a file is doing the work of multiple cohesive units; splitting along the receiver boundaries is the canonical Extract Class move._

