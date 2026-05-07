# PoC v2.6 — Multi-criteria ranking of cluster members

Root: `cli/slop`  |  Clusters: 54

### `fn_node` in `_structural/out_parameters.py` (8 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_process_python_function` (_structural/out_parameters.py) | 0.28 | 4 calls | 0.67 | **0.41** |
| `_process_c_function` (_structural/out_parameters.py) | 0.28 | 3 calls | 0.67 | **0.36** |
| `_process_cpp_function` (_structural/out_parameters.py) | 0.26 | 3 calls | 0.67 | **0.36** |
| `_extract_python_params` (_structural/out_parameters.py) | 0.25 | 1 calls | 0.33 | **0.21** |
| `_c_extract_pointer_params` (_structural/out_parameters.py) | 0.28 | 1 calls | 0.25 | **0.20** |
| `_cpp_extract_mutable_params` (_structural/out_parameters.py) | 0.26 | 1 calls | 0.25 | **0.19** |
| `_c_fn_name` (_structural/out_parameters.py) | 0.26 | 1 calls | 0.00 | **0.14** |
| `_cpp_fn_name` (_structural/out_parameters.py) | 0.25 | 1 calls | 0.00 | **0.14** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `pkg_files` in `_structural/robert.py` (6 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_compute_abstractness_ast` (_structural/robert.py) | 0.28 | 0 calls | 0.67 | **0.25** |
| `_compute_abstractness` (_structural/robert.py) | 0.10 | 0 calls | 1.00 | **0.24** |
| `_compute_abstractness_text` (_structural/robert.py) | 0.15 | 0 calls | 0.67 | **0.20** |
| `_split_classes_by_abstract_modifier` (_structural/robert.py) | 0.28 | 0 calls | 0.20 | **0.15** |
| `_split_cpp_classes_by_abstract` (_structural/robert.py) | 0.19 | 0 calls | 0.20 | **0.12** |
| `_count_query_matches` (_structural/robert.py) | 0.21 | 0 calls | 0.00 | **0.08** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `fn_node` in `_structural/stringly_typed.py` (5 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_process_c_function` (_structural/stringly_typed.py) | 0.41 | 2 calls | 1.00 | **0.43** |
| `_process_cpp_function` (_structural/stringly_typed.py) | 0.43 | 2 calls | 0.67 | **0.36** |
| `_process_python_function` (_structural/stringly_typed.py) | 0.28 | 3 calls | 0.67 | **0.36** |
| `_c_fn_name` (_structural/stringly_typed.py) | 0.36 | 1 calls | 0.33 | **0.25** |
| `_cpp_fn_name_local` (_structural/stringly_typed.py) | 0.34 | 1 calls | 0.00 | **0.18** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `file_paths` in `_structural/deps.py` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_resolve_edges` (_structural/deps.py) | 0.28 | 0 calls | 1.00 | **0.31** |
| `_reverse_adjacency` (_structural/deps.py) | 0.26 | 0 calls | 0.50 | **0.20** |
| `_extract_all_imports` (_structural/deps.py) | 0.25 | 0 calls | 0.00 | **0.10** |
| `_build_file_deps` (_structural/deps.py) | 0.18 | 0 calls | 0.00 | **0.07** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `body` in `_structural/sibling_calls.py` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_gather_callees` (_structural/sibling_calls.py) | 0.72 | 0 calls | 1.00 | **0.49** |
| `_gather_callees_c` (_structural/sibling_calls.py) | 0.67 | 0 calls | 1.00 | **0.47** |
| `_gather_callees_cpp` (_structural/sibling_calls.py) | 0.72 | 0 calls | 0.67 | **0.42** |
| `_gather_callees_ruby` (_structural/sibling_calls.py) | 0.65 | 0 calls | 0.67 | **0.39** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `cwd` in `_compose/git.py` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `git_log_numstat` (_compose/git.py) | 0.54 | 0 calls | 0.67 | **0.35** |
| `git_log_file_changes` (_compose/git.py) | 0.54 | 0 calls | 0.50 | **0.32** |
| `_run_git_log` (_compose/git.py) | 0.08 | 2 calls | 1.00 | **0.30** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `ctx` in `_lexical/identifier_singletons.py` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_collect_python_bindings` (_lexical/identifier_singletons.py) | 0.44 | 2 calls | 1.00 | **0.46** |
| `_collect_returns` (_lexical/identifier_singletons.py) | 0.44 | 2 calls | 0.50 | **0.36** |
| `_count_uses` (_lexical/identifier_singletons.py) | 0.40 | 2 calls | 0.00 | **0.24** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `functions` in `_structural/ccx.py` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_aggregate_file_metrics` (_structural/ccx.py) | 0.14 | 0 calls | 1.00 | **0.26** |
| `_count_zones` (_structural/ccx.py) | 0.18 | 0 calls | 0.00 | **0.07** |
| `_build_guidance` (_structural/ccx.py) | 0.16 | 0 calls | 0.00 | **0.06** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `body_node` in `_structural/out_parameters.py` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_cpp_find_mutations` (_structural/out_parameters.py) | 0.75 | 0 calls | 0.67 | **0.43** |
| `_c_find_mutations` (_structural/out_parameters.py) | 0.75 | 0 calls | 0.67 | **0.43** |
| `_find_python_mutations` (_structural/out_parameters.py) | 0.50 | 0 calls | 1.00 | **0.40** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `raw_rules` in `_compat.py` (5 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_collect_legacy_derivations` (_compat.py) | 0.19 | 1 calls | 0.67 | **0.25** |
| `_flatten_canonical_tables` (_compat.py) | 0.31 | 0 calls | 0.33 | **0.19** |
| `collect_prefix_overrides` (_compat.py) | 0.28 | 0 calls | 0.33 | **0.18** |
| `migrate_legacy_rule_tables` (_compat.py) | 0.16 | 0 calls | 0.50 | **0.16** |
| `_migrate_split_stutter_table` (_compat.py) | 0.19 | 1 calls | 0.00 | **0.12** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `text` in `color.py` (5 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `yellow` (color.py) | 1.00 | 0 calls | 1.00 | **0.60** |
| `red` (color.py) | 1.00 | 0 calls | 1.00 | **0.60** |
| `green` (color.py) | 1.00 | 0 calls | 1.00 | **0.60** |
| `dim` (color.py) | 1.00 | 0 calls | 0.00 | **0.40** |
| `bold` (color.py) | 1.00 | 0 calls | 0.00 | **0.40** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `result` in `output.py` (5 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `format_json` (output.py) | 0.12 | 10 calls | 0.50 | **0.55** |
| `_format_footer` (output.py) | 0.14 | 8 calls | 0.50 | **0.48** |
| `format_human` (output.py) | 0.16 | 3 calls | 1.00 | **0.38** |
| `_group_by_category` (output.py) | 0.16 | 1 calls | 0.33 | **0.17** |
| `format_quiet` (output.py) | 0.01 | 0 calls | 0.50 | **0.10** |

_Verdict: heterogeneous cluster — top and bottom members differ significantly. Consider whether the bottom members belong elsewhere._

### `rule_pairs` in `output.py` (5 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_rules_with_waivers` (output.py) | 0.27 | 0 calls | 0.67 | **0.24** |
| `_rules_with_violations` (output.py) | 0.27 | 0 calls | 0.67 | **0.24** |
| `_aggregate_category` (output.py) | 0.10 | 0 calls | 0.50 | **0.14** |
| `_category_header_extras` (output.py) | 0.14 | 0 calls | 0.33 | **0.12** |
| `_render_category_findings` (output.py) | 0.12 | 0 calls | 0.33 | **0.11** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `name` in `_lexical` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_classify` (_lexical/numbered_variants.py) | 0.16 | 1 calls | 1.00 | **0.30** |
| `split_identifier` (_lexical/identifier_tokens.py) | 0.12 | 1 calls | 1.00 | **0.29** |
| `_check_identifier` (_lexical/weasel_words.py) | 0.12 | 0 calls | 0.50 | **0.15** |
| `_lowercase_tokens` (_lexical/stutter.py) | 0.06 | 0 calls | 0.00 | **0.02** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `name` in `_structural` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_split` (_structural/composition.py) | 0.04 | 1 calls | 1.00 | **0.26** |
| `_compute_dit` (_structural/ck.py) | 0.06 | 0 calls | 1.00 | **0.22** |
| `_is_trivial_callee` (_structural/sibling_calls.py) | 0.04 | 2 calls | 0.00 | **0.10** |
| `_maybe_skip_self` (_structural/composition.py) | 0.02 | 0 calls | 0.00 | **0.01** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `raw` in `config.py` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_optional_number` (config.py) | 0.35 | 1 calls | 0.50 | **0.28** |
| `_build_waiver` (config.py) | 0.14 | 0 calls | 1.00 | **0.25** |
| `_optional_iso_date` (config.py) | 0.28 | 1 calls | 0.33 | **0.22** |
| `_required_string` (config.py) | 0.32 | 1 calls | 0.00 | **0.17** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `rule_name` in `output.py` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_category_for` (output.py) | 0.08 | 0 calls | 1.00 | **0.23** |
| `_render_waived` (output.py) | 0.26 | 0 calls | 0.50 | **0.21** |
| `_render_violations` (output.py) | 0.26 | 0 calls | 0.50 | **0.20** |
| `_short_name_for` (output.py) | 0.07 | 1 calls | 0.33 | **0.13** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `files` in `<root>` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `query_kernel` (_ast/query.py) | 0.13 | 0 calls | 1.00 | **0.25** |
| `_find_definitions` (_compose/usages.py) | 0.15 | 0 calls | 0.50 | **0.16** |
| `_resolve_packages` (_structural/robert.py) | 0.17 | 0 calls | 0.00 | **0.07** |
| `_is_go_main_package` (_structural/robert.py) | 0.11 | 0 calls | 0.00 | **0.04** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `name` in `<root>` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `load_language` (_ast/treesitter.py) | 0.14 | 0 calls | 1.00 | **0.25** |
| `canonical_categories` (_compat.py) | 0.31 | 0 calls | 0.50 | **0.23** |
| `canonical_rule_name` (_compat.py) | 0.31 | 0 calls | 0.33 | **0.19** |
| `_format_binary_status` (cli.py) | 0.08 | 0 calls | 0.00 | **0.03** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `output` in `<root>` (4 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_parse_log_output` (_compose/git.py) | 0.33 | 1 calls | 1.00 | **0.37** |
| `_parse_numstat_log_output` (_compose/git.py) | 0.35 | 1 calls | 0.75 | **0.33** |
| `_parse_fd_output` (_fs/find.py) | 0.30 | 1 calls | 0.67 | **0.29** |
| `_parse_rg_output` (_text/grep.py) | 0.26 | 1 calls | 0.67 | **0.28** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `root_node` in `_structural` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_walk_python_functions` (_structural/stringly_typed.py) | 0.56 | 0 calls | 1.00 | **0.42** |
| `_walk_python_functions` (_structural/out_parameters.py) | 0.56 | 0 calls | 1.00 | **0.42** |
| `_collect_functions` (_structural/clone_density.py) | 0.12 | 0 calls | 0.50 | **0.15** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `name` in `_util` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `check_tool` (_util/doctor.py) | 0.11 | 0 calls | 1.00 | **0.24** |
| `check_python_package` (_util/doctor.py) | 0.13 | 0 calls | 0.67 | **0.19** |
| `which` (_util/subprocess.py) | 0.06 | 0 calls | 0.00 | **0.02** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `args` in `cli.py` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_load_and_run` (cli.py) | 0.06 | 5 calls | 0.67 | **0.36** |
| `cmd_check` (cli.py) | 0.08 | 1 calls | 0.50 | **0.17** |
| `cmd_lint` (cli.py) | 0.03 | 0 calls | 0.50 | **0.11** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `violation` in `engine.py` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_matching_waiver` (engine.py) | 0.09 | 2 calls | 1.00 | **0.32** |
| `_value_allowed` (engine.py) | 0.09 | 2 calls | 0.50 | **0.22** |
| `_mark_waived` (engine.py) | 0.02 | 1 calls | 0.00 | **0.05** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `ctx` in `<root>` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `_check_python_params` (_lexical/type_tag_suffixes.py) | 0.20 | 6 calls | 0.33 | **0.39** |
| `_extract_python_docstring` (_lexical/boilerplate_docstrings.py) | 0.24 | 2 calls | 1.00 | **0.38** |
| `_extract_first_param` (_structural/composition.py) | 0.19 | 3 calls | 0.33 | **0.26** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

### `config` in `<root>` (3 members)

| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |
|---|---|---|---|---|
| `run_lint` (engine.py) | 0.11 | 6 calls | 0.50 | **0.35** |
| `required_binaries` (preflight.py) | 0.16 | 2 calls | 1.00 | **0.34** |
| `check_required_binaries` (preflight.py) | 0.16 | 0 calls | 0.67 | **0.20** |

_Verdict: cluster shares input but limited receiver-call evidence — likely strategy/transform family rather than missing class._

