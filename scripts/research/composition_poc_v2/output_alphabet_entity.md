# PoC v2.3 — Closed-alphabet entity recognition

Root: `cli/slop`  |  Functions: 463  |  Clusters: 24
Module-level dicts found: 53

## Closed alphabets ranked by entity-ness score

| Alphabet | Members | # Stems | # Files | # Dict-key matches | Score |
|---|---|---|---|---|---|
| {ast, c, cpp, csharp, default, extract, file, java, js, julia…} | 14 | 9 | 10 | 36 | **136** |
| {body, go, js, ruby, rust} | 5 | 2 | 3 | 31 | **100** |
| {abstractness, cbo, ccx, check, ck, cognitive, concepts, conf…} | 40 | 4 | 28 | 2 | **42** |
| {bold, classify, dim, extent, find, fingerprint, green, inten…} | 23 | 1 | 17 | 0 | **19** |
| {parse, query, scan, walk} | 4 | 1 | 7 | 0 | **9** |
| {extract, fn, function, get} | 4 | 1 | 7 | 0 | **9** |
| {fd, log, rg} | 3 | 1 | 3 | 1 | **8** |
| {functions, identifiers, returns, tokens} | 4 | 1 | 5 | 0 | **7** |
| {function, ruby, type} | 3 | 1 | 5 | 0 | **7** |
| {definitions, functions, kernel} | 3 | 1 | 5 | 0 | **7** |
| {collect, enumerate, find} | 3 | 1 | 5 | 0 | **7** |
| {guidance, waiver, waivers} | 3 | 1 | 4 | 0 | **6** |
| {identifier, package, tool} | 3 | 1 | 3 | 0 | **5** |
| {enclosing, process, walk} | 3 | 1 | 3 | 0 | **5** |
| {edges, languages, module, packages, target} | 5 | 1 | 3 | 0 | **5** |
| {docstring, params, superclasses} | 3 | 1 | 3 | 0 | **5** |
| {discover, load, rule} | 3 | 1 | 2 | 0 | **4** |
| {detect, filter, run} | 3 | 1 | 2 | 0 | **4** |
| {body, captures, name} | 3 | 1 | 2 | 0 | **4** |
| {footer, human, json, quiet} | 4 | 1 | 1 | 0 | **3** |
| {category, violations, waived} | 3 | 1 | 1 | 0 | **3** |
| {callers, identifiers, namespaces} | 3 | 1 | 1 | 0 | **3** |
| {block, if, node} | 3 | 1 | 1 | 0 | **3** |
| {ast, score, text} | 3 | 1 | 1 | 0 | **3** |

## Top alphabets — detail

### Alphabet `ast, c, cpp, csharp, default, extract, file, java, js, julia…` (score 136)
- 14 members, 9 stems, 10 files, 36 module-dict matches

  - stem `scan_*`: variants ['ast', 'c', 'cpp', 'file', 'python']
  - stem `*_name_extractor`: variants ['c', 'cpp', 'default', 'julia', 'ruby']
  - stem `*_is_function_node`: variants ['default', 'julia', 'ruby']
  - stem `*_function_name`: variants ['c', 'cpp', 'extract', 'ruby']
  - stem `extract_*_superclasses`: variants ['cpp', 'csharp', 'java', 'js', 'no', 'python', 'ruby', 'ts']

### Alphabet `body, go, js, ruby, rust` (score 100)
- 5 members, 2 stems, 3 files, 31 module-dict matches

  - stem `collect_*_classes`: variants ['body', 'go', 'ruby', 'rust']
  - stem `scan_*_text`: variants ['go', 'js', 'rust']

### Alphabet `abstractness, cbo, ccx, check, ck, cognitive, concepts, conf…` (score 42)
- 40 members, 4 stems, 28 files, 2 module-dict matches

  - stem `*_kernel`: variants ['ccx', 'ck', 'deps', 'find', 'grep', 'halstead', 'hotspots', 'npath']
  - stem `compute_*`: variants ['abstractness', 'cbo', 'concepts', 'confidence', 'distance', 'dit', 'halstead', 'instability']
  - stem `run_*`: variants ['ccx', 'ck', 'cognitive', 'coupling', 'cycles', 'cyclomatic', 'difficulty', 'distance']
  - stem `cmd_*`: variants ['check', 'doctor', 'hook', 'init', 'lint', 'rules', 'schema', 'skill']

### Alphabet `bold, classify, dim, extent, find, fingerprint, green, inten…` (score 19)
- 23 members, 1 stems, 17 files, 0 module-dict matches

  - stem `*`: variants ['bold', 'classify', 'dim', 'extent', 'find', 'fingerprint', 'green', 'intent']

### Alphabet `parse, query, scan, walk` (score 9)
- 4 members, 1 stems, 7 files, 0 module-dict matches

  - stem `*_file`: variants ['parse', 'query', 'scan', 'walk']

