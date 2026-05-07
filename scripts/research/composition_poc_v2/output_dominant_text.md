# PoC v2.1 — Dominant-text labeling

Root: `cli/slop`  |  Functions analyzed: 463  |  Clusters: 54

| Cluster (param) | Scope | Members | Modal token | Shared stem | Varying alphabet |
|---|---|---|---|---|---|
| `fn_node` | `_structural/out_parameters.py` | 8 | `process`×3 | — | — |
| `pkg_files` | `_structural/robert.py` | 6 | `compute`×3 | — | `ast`, `matches`, `modifier`, `text` |
| `fn_node` | `_structural/stringly_typed.py` | 5 | `process`×3 | `function`, `process` | `local` |
| `file_paths` | `_structural/deps.py` | 4 | `resolve`×1 | — | `adjacency`, `deps`, `edges`, `imports` |
| `body` | `_structural/sibling_calls.py` | 4 | `gather`×4 | `callees`, `gather` | `c`, `cpp`, `ruby` |
| `cwd` | `_compose/git.py` | 3 | `git`×3 | `git`, `log` | `changes`, `numstat` |
| `ctx` | `_lexical/identifier_singletons.py` | 3 | `collect`×2 | `collect` | `bindings`, `returns`, `uses` |
| `functions` | `_structural/ccx.py` | 3 | `aggregate`×1 | — | `guidance`, `metrics`, `zones` |
| `body_node` | `_structural/out_parameters.py` | 3 | `find`×3 | `find`, `mutations` | — |
| `raw_rules` | `_compat.py` | 5 | `collect`×2 | — | `derivations`, `overrides`, `table` |
| `text` | `color.py` | 5 | `red`×1 | — | `bold`, `dim`, `green`, `red`, `yellow` |
| `result` | `output.py` | 5 | `format`×4 | `format` | `category`, `footer`, `human`, `json`, `quiet` |
| `rule_pairs` | `output.py` | 5 | `category`×3 | `category` | `extras`, `findings`, `violations`, `waivers` |
| `name` | `_lexical` | 4 | `identifier`×2 | — | `classify`, `tokens` |
| `name` | `_structural` | 4 | `compute`×1 | — | `callee`, `dit`, `self`, `split` |
| `raw` | `config.py` | 4 | `optional`×2 | — | `date`, `number`, `string`, `waiver` |
| `rule_name` | `output.py` | 4 | `for`×2 | — | `violations`, `waived` |
| `files` | `<root>` | 4 | `query`×1 | — | `definitions`, `kernel`, `package`, `packages` |
| `name` | `<root>` | 4 | `canonical`×2 | — | `categories`, `language`, `name`, `status` |
| `output` | `<root>` | 4 | `parse`×4 | `output`, `parse` | — |
| `root_node` | `_structural` | 3 | `functions`×3 | `functions`, `python`, `walk` | — |
| `name` | `_util` | 3 | `check`×2 | `check` | `package`, `tool`, `which` |
| `args` | `cli.py` | 3 | `cmd`×2 | `cmd` | `check`, `lint`, `run` |
| `violation` | `engine.py` | 3 | `matching`×1 | — | `allowed`, `waived`, `waiver` |
| `ctx` | `<root>` | 3 | `extract`×2 | `extract`, `python` | `docstring`, `param`, `params` |
| `config` | `<root>` | 3 | `required`×2 | `binaries`, `required` | `lint` |

## Per-cluster detail

### `fn_node` in `_structural/out_parameters.py` (8 fns)

- Modal token: `process` (×3)
- Shared stem: _none_
- Varying alphabet: _none_
- Top tokens: {'process': 3, 'function': 3, 'extract': 3, 'params': 3, 'c': 3, 'cpp': 3, 'python': 2, 'fn': 2}
- Members: `_process_python_function`, `_extract_python_params`, `_process_c_function`, `_c_fn_name`, `_c_extract_pointer_params`, `_process_cpp_function`, `_cpp_fn_name`, `_cpp_extract_mutable_params`

### `pkg_files` in `_structural/robert.py` (6 fns)

- Modal token: `compute` (×3)
- Shared stem: _none_
- Varying alphabet: `ast`, `matches`, `modifier`, `text`
- Top tokens: {'compute': 3, 'abstractness': 3, 'split': 2, 'classes': 2, 'by': 2, 'abstract': 2, 'count': 1, 'query': 1}
- Members: `_compute_abstractness`, `_count_query_matches`, `_split_cpp_classes_by_abstract`, `_split_classes_by_abstract_modifier`, `_compute_abstractness_ast`, `_compute_abstractness_text`

### `fn_node` in `_structural/stringly_typed.py` (5 fns)

- Modal token: `process` (×3)
- Shared stem: `function`, `process`
- Varying alphabet: `local`
- Top tokens: {'process': 3, 'function': 3, 'c': 2, 'fn': 2, 'name': 2, 'cpp': 2, 'python': 1, 'local': 1}
- Members: `_process_python_function`, `_process_c_function`, `_c_fn_name`, `_process_cpp_function`, `_cpp_fn_name_local`

### `file_paths` in `_structural/deps.py` (4 fns)

- Modal token: `resolve` (×1)
- Shared stem: _none_
- Varying alphabet: `adjacency`, `deps`, `edges`, `imports`
- Top tokens: {'resolve': 1, 'edges': 1, 'reverse': 1, 'adjacency': 1, 'build': 1, 'file': 1, 'deps': 1, 'extract': 1}
- Members: `_resolve_edges`, `_reverse_adjacency`, `_build_file_deps`, `_extract_all_imports`

### `body` in `_structural/sibling_calls.py` (4 fns)

- Modal token: `gather` (×4)
- Shared stem: `callees`, `gather`
- Varying alphabet: `c`, `cpp`, `ruby`
- Top tokens: {'gather': 4, 'callees': 4, 'c': 1, 'cpp': 1, 'ruby': 1}
- Members: `_gather_callees`, `_gather_callees_c`, `_gather_callees_cpp`, `_gather_callees_ruby`

### `cwd` in `_compose/git.py` (3 fns)

- Modal token: `git` (×3)
- Shared stem: `git`, `log`
- Varying alphabet: `changes`, `numstat`
- Top tokens: {'git': 3, 'log': 3, 'run': 1, 'file': 1, 'changes': 1, 'numstat': 1}
- Members: `_run_git_log`, `git_log_file_changes`, `git_log_numstat`

### `ctx` in `_lexical/identifier_singletons.py` (3 fns)

- Modal token: `collect` (×2)
- Shared stem: `collect`
- Varying alphabet: `bindings`, `returns`, `uses`
- Top tokens: {'collect': 2, 'python': 1, 'bindings': 1, 'count': 1, 'uses': 1, 'returns': 1}
- Members: `_collect_python_bindings`, `_count_uses`, `_collect_returns`

### `functions` in `_structural/ccx.py` (3 fns)

- Modal token: `aggregate` (×1)
- Shared stem: _none_
- Varying alphabet: `guidance`, `metrics`, `zones`
- Top tokens: {'aggregate': 1, 'file': 1, 'metrics': 1, 'build': 1, 'guidance': 1, 'count': 1, 'zones': 1}
- Members: `_aggregate_file_metrics`, `_build_guidance`, `_count_zones`

### `body_node` in `_structural/out_parameters.py` (3 fns)

- Modal token: `find` (×3)
- Shared stem: `find`, `mutations`
- Varying alphabet: _none_
- Top tokens: {'find': 3, 'mutations': 3, 'python': 1, 'c': 1, 'cpp': 1}
- Members: `_find_python_mutations`, `_c_find_mutations`, `_cpp_find_mutations`

### `raw_rules` in `_compat.py` (5 fns)

- Modal token: `collect` (×2)
- Shared stem: _none_
- Varying alphabet: `derivations`, `overrides`, `table`
- Top tokens: {'collect': 2, 'tables': 2, 'legacy': 2, 'migrate': 2, 'prefix': 1, 'overrides': 1, 'flatten': 1, 'canonical': 1}
- Members: `collect_prefix_overrides`, `_flatten_canonical_tables`, `_collect_legacy_derivations`, `_migrate_split_stutter_table`, `migrate_legacy_rule_tables`

### `text` in `color.py` (5 fns)

- Modal token: `red` (×1)
- Shared stem: _none_
- Varying alphabet: `bold`, `dim`, `green`, `red`, `yellow`
- Top tokens: {'red': 1, 'green': 1, 'yellow': 1, 'bold': 1, 'dim': 1}
- Members: `red`, `green`, `yellow`, `bold`, `dim`

### `result` in `output.py` (5 fns)

- Modal token: `format` (×4)
- Shared stem: `format`
- Varying alphabet: `category`, `footer`, `human`, `json`, `quiet`
- Top tokens: {'format': 4, 'human': 1, 'group': 1, 'by': 1, 'category': 1, 'footer': 1, 'quiet': 1, 'json': 1}
- Members: `format_human`, `_group_by_category`, `_format_footer`, `format_quiet`, `format_json`

### `rule_pairs` in `output.py` (5 fns)

- Modal token: `category` (×3)
- Shared stem: `category`
- Varying alphabet: `extras`, `findings`, `violations`, `waivers`
- Top tokens: {'category': 3, 'rules': 2, 'with': 2, 'render': 1, 'findings': 1, 'violations': 1, 'waivers': 1, 'aggregate': 1}
- Members: `_render_category_findings`, `_rules_with_violations`, `_rules_with_waivers`, `_aggregate_category`, `_category_header_extras`

### `name` in `_lexical` (4 fns)

- Modal token: `identifier` (×2)
- Shared stem: _none_
- Varying alphabet: `classify`, `tokens`
- Top tokens: {'identifier': 2, 'split': 1, 'classify': 1, 'lowercase': 1, 'tokens': 1, 'check': 1}
- Members: `split_identifier`, `_classify`, `_lowercase_tokens`, `_check_identifier`

### `name` in `_structural` (4 fns)

- Modal token: `compute` (×1)
- Shared stem: _none_
- Varying alphabet: `callee`, `dit`, `self`, `split`
- Top tokens: {'compute': 1, 'dit': 1, 'split': 1, 'maybe': 1, 'skip': 1, 'self': 1, 'is': 1, 'trivial': 1}
- Members: `_compute_dit`, `_split`, `_maybe_skip_self`, `_is_trivial_callee`

### `raw` in `config.py` (4 fns)

- Modal token: `optional` (×2)
- Shared stem: _none_
- Varying alphabet: `date`, `number`, `string`, `waiver`
- Top tokens: {'optional': 2, 'build': 1, 'waiver': 1, 'required': 1, 'string': 1, 'number': 1, 'iso': 1, 'date': 1}
- Members: `_build_waiver`, `_required_string`, `_optional_number`, `_optional_iso_date`

### `rule_name` in `output.py` (4 fns)

- Modal token: `for` (×2)
- Shared stem: _none_
- Varying alphabet: `violations`, `waived`
- Top tokens: {'for': 2, 'render': 2, 'category': 1, 'short': 1, 'name': 1, 'violations': 1, 'waived': 1}
- Members: `_category_for`, `_short_name_for`, `_render_violations`, `_render_waived`

### `files` in `<root>` (4 fns)

- Modal token: `query` (×1)
- Shared stem: _none_
- Varying alphabet: `definitions`, `kernel`, `package`, `packages`
- Top tokens: {'query': 1, 'kernel': 1, 'find': 1, 'definitions': 1, 'resolve': 1, 'packages': 1, 'is': 1, 'go': 1}
- Members: `query_kernel`, `_find_definitions`, `_resolve_packages`, `_is_go_main_package`

### `name` in `<root>` (4 fns)

- Modal token: `canonical` (×2)
- Shared stem: _none_
- Varying alphabet: `categories`, `language`, `name`, `status`
- Top tokens: {'canonical': 2, 'load': 1, 'language': 1, 'rule': 1, 'name': 1, 'categories': 1, 'format': 1, 'binary': 1}
- Members: `load_language`, `canonical_rule_name`, `canonical_categories`, `_format_binary_status`

### `output` in `<root>` (4 fns)

- Modal token: `parse` (×4)
- Shared stem: `output`, `parse`
- Varying alphabet: _none_
- Top tokens: {'parse': 4, 'output': 4, 'log': 2, 'numstat': 1, 'fd': 1, 'rg': 1}
- Members: `_parse_log_output`, `_parse_numstat_log_output`, `_parse_fd_output`, `_parse_rg_output`

### `root_node` in `_structural` (3 fns)

- Modal token: `functions` (×3)
- Shared stem: `functions`, `python`, `walk`
- Varying alphabet: _none_
- Top tokens: {'functions': 3, 'walk': 2, 'python': 2, 'collect': 1}
- Members: `_collect_functions`, `_walk_python_functions`, `_walk_python_functions`

### `name` in `_util` (3 fns)

- Modal token: `check` (×2)
- Shared stem: `check`
- Varying alphabet: `package`, `tool`, `which`
- Top tokens: {'check': 2, 'tool': 1, 'python': 1, 'package': 1, 'which': 1}
- Members: `check_tool`, `check_python_package`, `which`

### `args` in `cli.py` (3 fns)

- Modal token: `cmd` (×2)
- Shared stem: `cmd`
- Varying alphabet: `check`, `lint`, `run`
- Top tokens: {'cmd': 2, 'load': 1, 'and': 1, 'run': 1, 'lint': 1, 'check': 1}
- Members: `_load_and_run`, `cmd_lint`, `cmd_check`

### `violation` in `engine.py` (3 fns)

- Modal token: `matching` (×1)
- Shared stem: _none_
- Varying alphabet: `allowed`, `waived`, `waiver`
- Top tokens: {'matching': 1, 'waiver': 1, 'value': 1, 'allowed': 1, 'mark': 1, 'waived': 1}
- Members: `_matching_waiver`, `_value_allowed`, `_mark_waived`

### `ctx` in `<root>` (3 fns)

- Modal token: `extract` (×2)
- Shared stem: `extract`, `python`
- Varying alphabet: `docstring`, `param`, `params`
- Top tokens: {'extract': 2, 'python': 2, 'docstring': 1, 'check': 1, 'params': 1, 'first': 1, 'param': 1}
- Members: `_extract_python_docstring`, `_check_python_params`, `_extract_first_param`

### `config` in `<root>` (3 fns)

- Modal token: `required` (×2)
- Shared stem: `binaries`, `required`
- Varying alphabet: `lint`
- Top tokens: {'required': 2, 'binaries': 2, 'run': 1, 'lint': 1, 'check': 1}
- Members: `run_lint`, `required_binaries`, `check_required_binaries`

