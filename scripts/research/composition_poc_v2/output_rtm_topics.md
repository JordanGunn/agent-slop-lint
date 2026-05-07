# PoC v2.5 — Latent topic modeling (RTM-style via LDA)

Root: `cli/slop`  |  Documents (functions): 447  |  Topics: 10

Vocabulary size: 683

## Discovered topics

- **Topic 0**: rule, result, violations, config, severity, root, threshold, errors
- **Topic 1**: lang, tree, file, errors, root, language, globs, parser
- **Topic 2**: tokens, scope, path, parts, str, lines, len, get
- **Topic 3**: files, matches, pkg, query, errors, language, str, list
- **Topic 4**: ctx, items, len, parent, file, cluster, str, ccx
- **Topic 5**: node, child, type, byte, content, declarator, start, inner
- **Topic 6**: path, str, raw, waiver, file, parser, print, target
- **Topic 7**: node, config, body, child, npath, walk, type, children
- **Topic 8**: entry, stack, node, str, file, annotation, list, set
- **Topic 9**: callees, content, len, shared, tree, line, score, findall

## Functions assigned to each topic

### Topic 0 (79 functions)
- `run_tersity` (rules/tersity.py)  —  weight 0.99
- `run_weighted` (rules/complexity.py)  —  weight 0.99
- `run_coupling` (rules/class_metrics.py)  —  weight 0.99
- `run_inheritance_depth` (rules/class_metrics.py)  —  weight 0.99
- `git_log_numstat` (_compose/git.py)  —  weight 0.99
- `run_inheritance_children` (rules/class_metrics.py)  —  weight 0.99
- `git_log_file_changes` (_compose/git.py)  —  weight 0.99
- `_select_rules` (engine.py)  —  weight 0.95
- _...and 71 more_

### Topic 1 (50 functions)
- `section_comment_kernel` (_structural/section_comments.py)  —  weight 1.00
- `usages_kernel` (_compose/usages.py)  —  weight 1.00
- `any_type_density_kernel` (_structural/any_type_density.py)  —  weight 0.99
- `identifier_token_kernel` (_lexical/identifier_tokens.py)  —  weight 0.99
- `prune_kernel` (_compose/prune.py)  —  weight 0.99
- `stutter_kernel` (_lexical/stutter.py)  —  weight 0.99
- `_analyze_files` (_compose/prune.py)  —  weight 0.99
- `local_imports_kernel` (_structural/local_imports.py)  —  weight 0.99
- _...and 42 more_

### Topic 2 (33 functions)
- `_check_identifier` (_lexical/weasel_words.py)  —  weight 0.99
- `_module_names_for_path` (_structural/deps.py)  —  weight 0.98
- `check_python_package` (_util/doctor.py)  —  weight 0.97
- `_check_module_name` (_lexical/weasel_words.py)  —  weight 0.97
- `walk` (_structural/ck.py)  —  weight 0.96
- `_classify_cluster` (_structural/composition.py)  —  weight 0.94
- `split_identifier` (_lexical/identifier_tokens.py)  —  weight 0.93
- `_scope_label` (_structural/composition.py)  —  weight 0.92
- _...and 25 more_

### Topic 3 (33 functions)
- `hotspots_kernel` (_compose/hotspots.py)  —  weight 1.00
- `robert_kernel` (_structural/robert.py)  —  weight 1.00
- `_compute_abstractness_ast` (_structural/robert.py)  —  weight 1.00
- `_split_classes_by_abstract_modifier` (_structural/robert.py)  —  weight 0.99
- `_empty_result` (_compose/hotspots.py)  —  weight 0.98
- `_assign_quadrants` (_compose/hotspots.py)  —  weight 0.98
- `_count_query_matches` (_structural/robert.py)  —  weight 0.98
- `_compute_confidence` (_compose/prune.py)  —  weight 0.98
- _...and 25 more_

### Topic 4 (29 functions)
- `_aggregate_file_metrics` (_structural/ccx.py)  —  weight 0.99
- `_cluster_patterns_by_alphabet` (_structural/composition.py)  —  weight 0.99
- `generate_default_config` (config.py)  —  weight 0.98
- `_interpret` (_structural/ccx.py)  —  weight 0.97
- `_interpret` (_structural/ck.py)  —  weight 0.97
- `_find_inheritance_pairs` (_structural/composition.py)  —  weight 0.97
- `_compute_zone` (_structural/ccx.py)  —  weight 0.93
- `find` (_structural/composition.py)  —  weight 0.87
- _...and 21 more_

### Topic 5 (111 functions)
- `_process_cpp_function` (_structural/stringly_typed.py)  —  weight 0.99
- `_cpp_extract_mutable_params` (_structural/out_parameters.py)  —  weight 0.99
- `_get_name` (_lexical/stutter.py)  —  weight 0.99
- `_fn_name` (_lexical/identifier_tokens.py)  —  weight 0.99
- `_fn_name` (_structural/magic_literals.py)  —  weight 0.99
- `_fn_name` (_structural/section_comments.py)  —  weight 0.99
- `_process_c_function` (_structural/stringly_typed.py)  —  weight 0.99
- `_c_extract_pointer_params` (_structural/out_parameters.py)  —  weight 0.99
- _...and 103 more_

### Topic 6 (37 functions)
- `create_parser` (cli.py)  —  weight 0.99
- `_parse_header` (_compose/git.py)  —  weight 0.98
- `_resolve_module` (_structural/deps.py)  —  weight 0.98
- `_copy_tree` (cli.py)  —  weight 0.97
- `_interpret` (_structural/robert.py)  —  weight 0.96
- `_mark_waived` (engine.py)  —  weight 0.95
- `_parse_numstat_log_output` (_compose/git.py)  —  weight 0.95
- `_print_missing_binaries` (cli.py)  —  weight 0.94
- _...and 29 more_

### Topic 7 (42 functions)
- `_npath_of_node` (_structural/npath.py)  —  weight 0.99
- `_npath_of_if` (_structural/npath.py)  —  weight 0.99
- `_collect_legacy_derivations` (_compat.py)  —  weight 0.98
- `_migrate_split_stutter_table` (_compat.py)  —  weight 0.98
- `_iter_cases` (_structural/npath.py)  —  weight 0.96
- `migrate_legacy_rule_tables` (_compat.py)  —  weight 0.96
- `_compute_halstead` (_structural/halstead.py)  —  weight 0.92
- `_is_leaf_legacy_table` (_compat.py)  —  weight 0.91
- _...and 34 more_

### Topic 8 (27 functions)
- `_detect_cycles` (_structural/deps.py)  —  weight 0.99
- `strongconnect` (_structural/deps.py)  —  weight 0.98
- `_build_file_deps` (_structural/deps.py)  —  weight 0.98
- `_resolve_edges` (_structural/deps.py)  —  weight 0.89
- `_walk_python_functions` (_structural/stringly_typed.py)  —  weight 0.82
- `extract_captures` (_ast/treesitter.py)  —  weight 0.79
- `_walk_python_functions` (_structural/out_parameters.py)  —  weight 0.78
- `_pop_scc` (_structural/deps.py)  —  weight 0.72
- _...and 19 more_

### Topic 9 (6 functions)
- `_analyze_ruby_file` (_structural/sibling_calls.py)  —  weight 0.99
- `_analyze_python_file` (_structural/sibling_calls.py)  —  weight 0.99
- `_analyze_c_file` (_structural/sibling_calls.py)  —  weight 0.99
- `_compute_abstractness_text` (_structural/robert.py)  —  weight 0.90
- `_analyze_cpp_file` (_structural/sibling_calls.py)  —  weight 0.80
- `run_sibling_call_redundancy` (rules/sibling_calls.py)  —  weight 0.50
- File concentration: {'_structural/sibling_calls.py': 4, '_structural/robert.py': 1, 'rules/sibling_calls.py': 1}

