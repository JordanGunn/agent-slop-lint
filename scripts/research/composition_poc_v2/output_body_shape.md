# PoC v2.2 — Body-shape signatures

Root: `cli/slop`  |  Indexed 456 function bodies  |  Clusters: 54

| Cluster | Scope | Members | Mean pairwise Jaccard (3-gram) | Verdict |
|---|---|---|---|---|
| `fn_node` | `_structural/out_parameters.py` | 8 | 0.27 | low (heterogeneous) |
| `pkg_files` | `_structural/robert.py` | 6 | 0.20 | low (heterogeneous) |
| `fn_node` | `_structural/stringly_typed.py` | 5 | 0.37 | low (heterogeneous) |
| `file_paths` | `_structural/deps.py` | 4 | 0.24 | low (heterogeneous) |
| `body` | `_structural/sibling_calls.py` | 4 | 0.69 | moderate |
| `cwd` | `_compose/git.py` | 3 | 0.39 | low (heterogeneous) |
| `ctx` | `_lexical/identifier_singletons.py` | 3 | 0.43 | moderate |
| `functions` | `_structural/ccx.py` | 3 | 0.16 | low (heterogeneous) |
| `body_node` | `_structural/out_parameters.py` | 3 | 0.67 | moderate |
| `raw_rules` | `_compat.py` | 5 | 0.23 | low (heterogeneous) |
| `text` | `color.py` | 5 | 1.00 | **high cohesion** (clone family) |
| `result` | `output.py` | 5 | 0.12 | low (heterogeneous) |
| `rule_pairs` | `output.py` | 5 | 0.18 | low (heterogeneous) |
| `name` | `_lexical` | 4 | 0.11 | low (heterogeneous) |
| `name` | `_structural` | 4 | 0.04 | low (heterogeneous) |
| `raw` | `config.py` | 4 | 0.27 | low (heterogeneous) |
| `rule_name` | `output.py` | 4 | 0.17 | low (heterogeneous) |
| `files` | `<root>` | 4 | 0.14 | low (heterogeneous) |
| `name` | `<root>` | 4 | 0.21 | low (heterogeneous) |
| `output` | `<root>` | 4 | 0.31 | low (heterogeneous) |
| `root_node` | `_structural` | 3 | 0.41 | moderate |
| `name` | `_util` | 3 | 0.10 | low (heterogeneous) |
| `args` | `cli.py` | 3 | 0.05 | low (heterogeneous) |
| `violation` | `engine.py` | 3 | 0.07 | low (heterogeneous) |
| `ctx` | `<root>` | 3 | 0.21 | low (heterogeneous) |
| `config` | `<root>` | 3 | 0.14 | low (heterogeneous) |

## Per-cluster detail

### `fn_node` in `_structural/out_parameters.py` (mean Jaccard 0.27)

- `_process_python_function` (_structural/out_parameters.py): 51 3-grams
- `_extract_python_params` (_structural/out_parameters.py): 94 3-grams
- `_process_c_function` (_structural/out_parameters.py): 36 3-grams
- `_c_fn_name` (_structural/out_parameters.py): 55 3-grams
- `_c_extract_pointer_params` (_structural/out_parameters.py): 103 3-grams
- `_process_cpp_function` (_structural/out_parameters.py): 43 3-grams
- `_cpp_fn_name` (_structural/out_parameters.py): 59 3-grams
- `_cpp_extract_mutable_params` (_structural/out_parameters.py): 126 3-grams
- Shared 3-grams (in all members): 6
    - `expression_statement → expression_statement → assignment`
    - `block → expression_statement → expression_statement`
    - `block → return_statement → return`
    - `expression_statement → assignment → call`
    - `argument_list → if_statement → if`
    - `call → attribute → argument_list`

### `pkg_files` in `_structural/robert.py` (mean Jaccard 0.20)

- `_compute_abstractness` (_structural/robert.py): 27 3-grams
- `_count_query_matches` (_structural/robert.py): 47 3-grams
- `_split_cpp_classes_by_abstract` (_structural/robert.py): 186 3-grams
- `_split_classes_by_abstract_modifier` (_structural/robert.py): 77 3-grams
- `_compute_abstractness_ast` (_structural/robert.py): 95 3-grams
- `_compute_abstractness_text` (_structural/robert.py): 88 3-grams
- Shared 3-grams (in all members): 3
    - `expression_statement → call → attribute`
    - `call → attribute → argument_list`
    - `block → expression_statement → call`

### `fn_node` in `_structural/stringly_typed.py` (mean Jaccard 0.37)

- `_process_python_function` (_structural/stringly_typed.py): 106 3-grams
- `_process_c_function` (_structural/stringly_typed.py): 120 3-grams
- `_c_fn_name` (_structural/stringly_typed.py): 55 3-grams
- `_process_cpp_function` (_structural/stringly_typed.py): 135 3-grams
- `_cpp_fn_name_local` (_structural/stringly_typed.py): 59 3-grams
- Shared 3-grams (in all members): 20
    - `if_statement → if → comparison_operator`
    - `if → comparison_operator → attribute`
    - `slice → attribute → attribute`
    - `block → expression_statement → assignment`
    - `attribute → attribute → argument_list`
    - `call → attribute → subscript`

### `file_paths` in `_structural/deps.py` (mean Jaccard 0.24)

- `_resolve_edges` (_structural/deps.py): 49 3-grams
- `_reverse_adjacency` (_structural/deps.py): 41 3-grams
- `_build_file_deps` (_structural/deps.py): 57 3-grams
- `_extract_all_imports` (_structural/deps.py): 78 3-grams
- Shared 3-grams (in all members): 10
    - `expression_statement → expression_statement → assignment`
    - `for_statement → for → in`
    - `for → in → block`
    - `block → expression_statement → expression_statement`
    - `type → generic_type → type_parameter`
    - `expression_statement → call → attribute`

### `body` in `_structural/sibling_calls.py` (mean Jaccard 0.69)

- `_gather_callees` (_structural/sibling_calls.py): 58 3-grams
- `_gather_callees_c` (_structural/sibling_calls.py): 54 3-grams
- `_gather_callees_cpp` (_structural/sibling_calls.py): 75 3-grams
- `_gather_callees_ruby` (_structural/sibling_calls.py): 75 3-grams
- Shared 3-grams (in all members): 46
    - `expression_statement → expression_statement → assignment`
    - `call → argument_list → expression_statement`
    - `block → expression_statement → expression_statement`
    - `if_statement → if → comparison_operator`
    - `argument_list → keyword_argument → if_statement`
    - `argument_list → block → expression_statement`

### `cwd` in `_compose/git.py` (mean Jaccard 0.39)

- `_run_git_log` (_compose/git.py): 123 3-grams
- `git_log_file_changes` (_compose/git.py): 29 3-grams
- `git_log_numstat` (_compose/git.py): 29 3-grams
- Shared 3-grams (in all members): 11
    - `assignment → call → argument_list`
    - `call → argument_list → expression_statement`
    - `block → return_statement → return`
    - `argument_list → expression_statement → assignment`
    - `is → block → return_statement`
    - `expression_statement → assignment → call`

### `ctx` in `_lexical/identifier_singletons.py` (mean Jaccard 0.43)

- `_collect_python_bindings` (_lexical/identifier_singletons.py): 51 3-grams
- `_count_uses` (_lexical/identifier_singletons.py): 86 3-grams
- `_collect_returns` (_lexical/identifier_singletons.py): 56 3-grams
- Shared 3-grams (in all members): 31
    - `expression_statement → expression_statement → assignment`
    - `call → argument_list → expression_statement`
    - `block → expression_statement → expression_statement`
    - `if_statement → if → comparison_operator`
    - `function_definition → def → parameters`
    - `generic_type → type_parameter → type`

### `functions` in `_structural/ccx.py` (mean Jaccard 0.16)

- `_aggregate_file_metrics` (_structural/ccx.py): 73 3-grams
- `_build_guidance` (_structural/ccx.py): 43 3-grams
- `_count_zones` (_structural/ccx.py): 30 3-grams
- Shared 3-grams (in all members): 11
    - `expression_statement → expression_statement → assignment`
    - `for_statement → for → in`
    - `for → in → block`
    - `block → expression_statement → expression_statement`
    - `type → generic_type → type_parameter`
    - `generic_type → type_parameter → type`

### `body_node` in `_structural/out_parameters.py` (mean Jaccard 0.67)

- `_find_python_mutations` (_structural/out_parameters.py): 66 3-grams
- `_c_find_mutations` (_structural/out_parameters.py): 48 3-grams
- `_cpp_find_mutations` (_structural/out_parameters.py): 48 3-grams
- Shared 3-grams (in all members): 38
    - `expression_statement → expression_statement → assignment`
    - `block → expression_statement → expression_statement`
    - `if_statement → if → comparison_operator`
    - `generic_type → type_parameter → type`
    - `if → comparison_operator → attribute`
    - `call → argument_list → keyword_argument`

### `raw_rules` in `_compat.py` (mean Jaccard 0.23)

- `collect_prefix_overrides` (_compat.py): 81 3-grams
- `_flatten_canonical_tables` (_compat.py): 62 3-grams
- `_collect_legacy_derivations` (_compat.py): 49 3-grams
- `_migrate_split_stutter_table` (_compat.py): 37 3-grams
- `migrate_legacy_rule_tables` (_compat.py): 41 3-grams
- Shared 3-grams (in all members): 4
    - `expression_statement → assignment → type`
    - `expression_statement → expression_statement → assignment`
    - `call → attribute → argument_list`
    - `block → expression_statement → expression_statement`

### `text` in `color.py` (mean Jaccard 1.00)

- `red` (color.py): 3 3-grams
- `green` (color.py): 3 3-grams
- `yellow` (color.py): 3 3-grams
- `bold` (color.py): 3 3-grams
- `dim` (color.py): 3 3-grams
- Shared 3-grams (in all members): 3
    - `return_statement → return → call`
    - `block → return_statement → return`
    - `return → call → argument_list`

### `result` in `output.py` (mean Jaccard 0.12)

- `format_human` (output.py): 51 3-grams
- `_group_by_category` (output.py): 34 3-grams
- `_format_footer` (output.py): 53 3-grams
- `format_quiet` (output.py): 4 3-grams
- `format_json` (output.py): 48 3-grams

### `rule_pairs` in `output.py` (mean Jaccard 0.18)

- `_render_category_findings` (output.py): 25 3-grams
- `_rules_with_violations` (output.py): 15 3-grams
- `_rules_with_waivers` (output.py): 15 3-grams
- `_aggregate_category` (output.py): 51 3-grams
- `_category_header_extras` (output.py): 49 3-grams
- Shared 3-grams (in all members): 1
    - `for → pattern_list → in`

### `name` in `_lexical` (mean Jaccard 0.11)

- `split_identifier` (_lexical/identifier_tokens.py): 17 3-grams
- `_classify` (_lexical/numbered_variants.py): 76 3-grams
- `_lowercase_tokens` (_lexical/stutter.py): 11 3-grams
- `_check_identifier` (_lexical/weasel_words.py): 65 3-grams
- Shared 3-grams (in all members): 1
    - `call → attribute → argument_list`

### `name` in `_structural` (mean Jaccard 0.04)

- `_compute_dit` (_structural/ck.py): 51 3-grams
- `_split` (_structural/composition.py): 18 3-grams
- `_maybe_skip_self` (_structural/composition.py): 4 3-grams
- `_is_trivial_callee` (_structural/sibling_calls.py): 26 3-grams

### `raw` in `config.py` (mean Jaccard 0.27)

- `_build_waiver` (config.py): 70 3-grams
- `_required_string` (config.py): 25 3-grams
- `_optional_number` (config.py): 33 3-grams
- `_optional_iso_date` (config.py): 41 3-grams
- Shared 3-grams (in all members): 9
    - `raise_statement → raise → call`
    - `raise → call → argument_list`
    - `block → raise_statement → raise`
    - `expression_statement → assignment → call`
    - `argument_list → if_statement → if`
    - `call → attribute → argument_list`

### `rule_name` in `output.py` (mean Jaccard 0.17)

- `_category_for` (output.py): 17 3-grams
- `_short_name_for` (output.py): 13 3-grams
- `_render_violations` (output.py): 82 3-grams
- `_render_waived` (output.py): 84 3-grams
- Shared 3-grams (in all members): 2
    - `call → attribute → argument_list`
    - `if_statement → if → comparison_operator`

### `files` in `<root>` (mean Jaccard 0.14)

- `query_kernel` (_ast/query.py): 91 3-grams
- `_find_definitions` (_compose/usages.py): 108 3-grams
- `_resolve_packages` (_structural/robert.py): 53 3-grams
- `_is_go_main_package` (_structural/robert.py): 37 3-grams
- Shared 3-grams (in all members): 5
    - `for_statement → for → in`
    - `for → in → block`
    - `expression_statement → assignment → call`
    - `call → attribute → argument_list`
    - `block → expression_statement → assignment`

### `name` in `<root>` (mean Jaccard 0.21)

- `load_language` (_ast/treesitter.py): 59 3-grams
- `canonical_rule_name` (_compat.py): 15 3-grams
- `canonical_categories` (_compat.py): 16 3-grams
- `_format_binary_status` (cli.py): 52 3-grams
- Shared 3-grams (in all members): 3
    - `expression_statement → assignment → call`
    - `call → attribute → argument_list`
    - `assignment → call → attribute`

### `output` in `<root>` (mean Jaccard 0.31)

- `_parse_log_output` (_compose/git.py): 68 3-grams
- `_parse_numstat_log_output` (_compose/git.py): 82 3-grams
- `_parse_fd_output` (_fs/find.py): 52 3-grams
- `_parse_rg_output` (_text/grep.py): 55 3-grams
- Shared 3-grams (in all members): 17
    - `continue_statement → continue → expression_statement`
    - `for_statement → for → in`
    - `continue → expression_statement → assignment`
    - `expression_statement → call → attribute`
    - `if → not_operator → not`
    - `not_operator → not → block`

### `root_node` in `_structural` (mean Jaccard 0.41)

- `_collect_functions` (_structural/clone_density.py): 48 3-grams
- `_walk_python_functions` (_structural/out_parameters.py): 26 3-grams
- `_walk_python_functions` (_structural/stringly_typed.py): 26 3-grams
- Shared 3-grams (in all members): 8
    - `assignment → call → argument_list`
    - `call → argument_list → expression_statement`
    - `expression_statement → call → attribute`
    - `expression_statement → assignment → call`
    - `if_statement → if → comparison_operator`
    - `argument_list → if_statement → if`

### `name` in `_util` (mean Jaccard 0.10)

- `check_tool` (_util/doctor.py): 83 3-grams
- `check_python_package` (_util/doctor.py): 40 3-grams
- `which` (_util/subprocess.py): 15 3-grams
- Shared 3-grams (in all members): 3
    - `expression_statement → assignment → call`
    - `call → attribute → argument_list`
    - `assignment → call → attribute`

### `args` in `cli.py` (mean Jaccard 0.05)

- `_load_and_run` (cli.py): 74 3-grams
- `cmd_lint` (cli.py): 3 3-grams
- `cmd_check` (cli.py): 70 3-grams
- Shared 3-grams (in all members): 1
    - `block → return_statement → return`

### `violation` in `engine.py` (mean Jaccard 0.07)

- `_matching_waiver` (engine.py): 25 3-grams
- `_value_allowed` (engine.py): 25 3-grams
- `_mark_waived` (engine.py): 18 3-grams
- Shared 3-grams (in all members): 1
    - `call → argument_list → attribute`

### `ctx` in `<root>` (mean Jaccard 0.21)

- `_extract_python_docstring` (_lexical/boilerplate_docstrings.py): 47 3-grams
- `_check_python_params` (_lexical/type_tag_suffixes.py): 87 3-grams
- `_extract_first_param` (_structural/composition.py): 99 3-grams
- Shared 3-grams (in all members): 19
    - `expression_statement → expression_statement → assignment`
    - `block → expression_statement → expression_statement`
    - `if_statement → if → comparison_operator`
    - `if → comparison_operator → attribute`
    - `slice → attribute → attribute`
    - `block → expression_statement → assignment`

### `config` in `<root>` (mean Jaccard 0.14)

- `run_lint` (engine.py): 114 3-grams
- `required_binaries` (preflight.py): 53 3-grams
- `check_required_binaries` (preflight.py): 40 3-grams
- Shared 3-grams (in all members): 9
    - `expression_statement → expression_statement → assignment`
    - `block → expression_statement → expression_statement`
    - `type → generic_type → type_parameter`
    - `expression_statement → assignment → call`
    - `call → attribute → call`
    - `generic_type → type_parameter → type`

