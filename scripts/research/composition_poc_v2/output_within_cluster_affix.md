# PoC v2.4 — Within-cluster affix re-detection

Root: `cli/slop`  |  Clusters: 54

| Cluster (param) | Scope | Members | Affix patterns within | Coverage |
|---|---|---|---|---|
| `fn_node` | `_structural/out_parameters.py` | 8 | process_*_function → {c, cpp, python}; *_fn_name → {c, cpp} | 62% |
| `pkg_files` | `_structural/robert.py` | 6 | compute_abstractness_* → {ast, text} | 33% |
| `fn_node` | `_structural/stringly_typed.py` | 5 | process_*_function → {c, cpp, python} | 60% |
| `file_paths` | `_structural/deps.py` | 4 | — | 0% |
| `body` | `_structural/sibling_calls.py` | 4 | gather_callees_* → {c, cpp, ruby} | 75% |
| `cwd` | `_compose/git.py` | 3 | — | 0% |
| `ctx` | `_lexical/identifier_singletons.py` | 3 | — | 0% |
| `functions` | `_structural/ccx.py` | 3 | — | 0% |
| `body_node` | `_structural/out_parameters.py` | 3 | *_find_mutations → {c, cpp} | 67% |
| `raw_rules` | `_compat.py` | 5 | — | 0% |
| `text` | `color.py` | 5 | * → {bold, dim, green, red, yellow} | 100% |
| `result` | `output.py` | 5 | format_* → {footer, human, json, quiet} | 80% |
| `rule_pairs` | `output.py` | 5 | rules_with_* → {violations, waivers} | 40% |
| `name` | `_lexical` | 4 | *_identifier → {check, split} | 50% |
| `name` | `_structural` | 4 | — | 0% |
| `raw` | `config.py` | 4 | — | 0% |
| `rule_name` | `output.py` | 4 | render_* → {violations, waived} | 50% |
| `files` | `<root>` | 4 | — | 0% |
| `name` | `<root>` | 4 | — | 0% |
| `output` | `<root>` | 4 | parse_*_output → {fd, log, rg} | 75% |
| `root_node` | `_structural` | 3 | — | 0% |
| `name` | `_util` | 3 | — | 0% |
| `args` | `cli.py` | 3 | cmd_* → {check, lint} | 67% |
| `violation` | `engine.py` | 3 | — | 0% |
| `ctx` | `<root>` | 3 | — | 0% |
| `config` | `<root>` | 3 | — | 0% |

## Per-cluster detail

### `fn_node` in `_structural/out_parameters.py` (coverage 62%)

- Members: `_process_python_function`, `_extract_python_params`, `_process_c_function`, `_c_fn_name`, `_c_extract_pointer_params`, `_process_cpp_function`, `_cpp_fn_name`, `_cpp_extract_mutable_params`
- Affix patterns (2):
  - stem `process_*_function`, alphabet `['c', 'cpp', 'python']`
  - stem `*_fn_name`, alphabet `['c', 'cpp']`

### `pkg_files` in `_structural/robert.py` (coverage 33%)

- Members: `_compute_abstractness`, `_count_query_matches`, `_split_cpp_classes_by_abstract`, `_split_classes_by_abstract_modifier`, `_compute_abstractness_ast`, `_compute_abstractness_text`
- Affix patterns (1):
  - stem `compute_abstractness_*`, alphabet `['ast', 'text']`

### `fn_node` in `_structural/stringly_typed.py` (coverage 60%)

- Members: `_process_python_function`, `_process_c_function`, `_c_fn_name`, `_process_cpp_function`, `_cpp_fn_name_local`
- Affix patterns (1):
  - stem `process_*_function`, alphabet `['c', 'cpp', 'python']`

### `file_paths` in `_structural/deps.py` (coverage 0%)

- Members: `_resolve_edges`, `_reverse_adjacency`, `_build_file_deps`, `_extract_all_imports`
- _No affix pattern within cluster — heterogeneous helpers._

### `body` in `_structural/sibling_calls.py` (coverage 75%)

- Members: `_gather_callees`, `_gather_callees_c`, `_gather_callees_cpp`, `_gather_callees_ruby`
- Affix patterns (1):
  - stem `gather_callees_*`, alphabet `['c', 'cpp', 'ruby']`

### `cwd` in `_compose/git.py` (coverage 0%)

- Members: `_run_git_log`, `git_log_file_changes`, `git_log_numstat`
- _No affix pattern within cluster — heterogeneous helpers._

### `ctx` in `_lexical/identifier_singletons.py` (coverage 0%)

- Members: `_collect_python_bindings`, `_count_uses`, `_collect_returns`
- _No affix pattern within cluster — heterogeneous helpers._

### `functions` in `_structural/ccx.py` (coverage 0%)

- Members: `_aggregate_file_metrics`, `_build_guidance`, `_count_zones`
- _No affix pattern within cluster — heterogeneous helpers._

### `body_node` in `_structural/out_parameters.py` (coverage 67%)

- Members: `_find_python_mutations`, `_c_find_mutations`, `_cpp_find_mutations`
- Affix patterns (1):
  - stem `*_find_mutations`, alphabet `['c', 'cpp']`

### `raw_rules` in `_compat.py` (coverage 0%)

- Members: `collect_prefix_overrides`, `_flatten_canonical_tables`, `_collect_legacy_derivations`, `_migrate_split_stutter_table`, `migrate_legacy_rule_tables`
- _No affix pattern within cluster — heterogeneous helpers._

### `text` in `color.py` (coverage 100%)

- Members: `red`, `green`, `yellow`, `bold`, `dim`
- Affix patterns (1):
  - stem `*`, alphabet `['bold', 'dim', 'green', 'red', 'yellow']`

### `result` in `output.py` (coverage 80%)

- Members: `format_human`, `_group_by_category`, `_format_footer`, `format_quiet`, `format_json`
- Affix patterns (1):
  - stem `format_*`, alphabet `['footer', 'human', 'json', 'quiet']`

### `rule_pairs` in `output.py` (coverage 40%)

- Members: `_render_category_findings`, `_rules_with_violations`, `_rules_with_waivers`, `_aggregate_category`, `_category_header_extras`
- Affix patterns (1):
  - stem `rules_with_*`, alphabet `['violations', 'waivers']`

### `name` in `_lexical` (coverage 50%)

- Members: `split_identifier`, `_classify`, `_lowercase_tokens`, `_check_identifier`
- Affix patterns (1):
  - stem `*_identifier`, alphabet `['check', 'split']`

### `name` in `_structural` (coverage 0%)

- Members: `_compute_dit`, `_split`, `_maybe_skip_self`, `_is_trivial_callee`
- _No affix pattern within cluster — heterogeneous helpers._

### `raw` in `config.py` (coverage 0%)

- Members: `_build_waiver`, `_required_string`, `_optional_number`, `_optional_iso_date`
- _No affix pattern within cluster — heterogeneous helpers._

### `rule_name` in `output.py` (coverage 50%)

- Members: `_category_for`, `_short_name_for`, `_render_violations`, `_render_waived`
- Affix patterns (1):
  - stem `render_*`, alphabet `['violations', 'waived']`

### `files` in `<root>` (coverage 0%)

- Members: `query_kernel`, `_find_definitions`, `_resolve_packages`, `_is_go_main_package`
- _No affix pattern within cluster — heterogeneous helpers._

### `name` in `<root>` (coverage 0%)

- Members: `load_language`, `canonical_rule_name`, `canonical_categories`, `_format_binary_status`
- _No affix pattern within cluster — heterogeneous helpers._

### `output` in `<root>` (coverage 75%)

- Members: `_parse_log_output`, `_parse_numstat_log_output`, `_parse_fd_output`, `_parse_rg_output`
- Affix patterns (1):
  - stem `parse_*_output`, alphabet `['fd', 'log', 'rg']`

### `root_node` in `_structural` (coverage 0%)

- Members: `_collect_functions`, `_walk_python_functions`, `_walk_python_functions`
- _No affix pattern within cluster — heterogeneous helpers._

### `name` in `_util` (coverage 0%)

- Members: `check_tool`, `check_python_package`, `which`
- _No affix pattern within cluster — heterogeneous helpers._

### `args` in `cli.py` (coverage 67%)

- Members: `_load_and_run`, `cmd_lint`, `cmd_check`
- Affix patterns (1):
  - stem `cmd_*`, alphabet `['check', 'lint']`

### `violation` in `engine.py` (coverage 0%)

- Members: `_matching_waiver`, `_value_allowed`, `_mark_waived`
- _No affix pattern within cluster — heterogeneous helpers._

### `ctx` in `<root>` (coverage 0%)

- Members: `_extract_python_docstring`, `_check_python_params`, `_extract_first_param`
- _No affix pattern within cluster — heterogeneous helpers._

### `config` in `<root>` (coverage 0%)

- Members: `run_lint`, `required_binaries`, `check_required_binaries`
- _No affix pattern within cluster — heterogeneous helpers._

