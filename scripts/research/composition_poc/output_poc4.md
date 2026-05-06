# composition.entity_surface_area — candidate missing classes

This report enumerates the surface area of each candidate entity in the alphabet. An entity with both data references (registry keys, config entries) and behaviour references (functions tagged with the entity name) is a textbook missing-class signature: data and behaviour scattered across files that should be bundled per-entity.

**Alphabet under analysis** (14 entities): `c`, `c_sharp`, `cpp`, `csharp`, `go`, `java`, `javascript`, `js`, `julia`, `python`, `ruby`, `rust`, `ts`, `typescript`

## Headline diagnosis

**14 entities** from the alphabet have non-zero surface area. Across these entities, **98 data references** and **49 behaviour references** are scattered across the scanned files.

This pattern — same alphabet of entities referenced as both data and behaviour, no shared abstraction binding them — is the signature of a missing class. Each entity is implicitly a class instance whose data and methods have been scattered.

**Recommended compositional mechanism**: introduce a first-class entity (class, dataclass, or trait). Each alphabet value becomes an instance or subclass. Data references become fields on the instance; behaviour references become methods.

## Per-entity surface area

### Entity: `ruby`

- **Total surface area**: 10 data references + 12 behaviour references = 22 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_ruby_find_method_name` (ccx.py:310)
- `_ruby_name_extractor` (ccx.py:340)
- `_ruby_is_function_node` (ccx.py:361)
- `_ruby_find_method_name` (npath.py:226)
- `_ruby_name_extractor` (npath.py:248)
- `_ruby_is_function_node` (npath.py:262)
- `_ruby_find_method_name` (halstead.py:227)
- `_ruby_name_extractor` (halstead.py:249)
- `_ruby_is_function_node` (halstead.py:263)
- `_extract_ruby_superclasses` (ck.py:292)
- … and 2 more

**Data (registry / config / dict-key occurrences):**

- ccx.py:666 — `"ruby": _LangConfig(`
- ccx.py:745 — `"ruby": ["**/*.rb"],`
- npath.py:474 — `"ruby": _NpathLangConfig(`
- npath.py:539 — `"ruby": ["**/*.rb"],`
- halstead.py:527 — `"ruby": _HalsteadLangConfig(`
- halstead.py:631 — `"ruby": ["**/*.rb"],`
- ck.py:678 — `if cm.language != "ruby":`
- ck.py:830 — `"ruby": _CkLangConfig(`
- ck.py:856 — `"ruby": ["**/*.rb"],`
- ck.py:940 — `elif lang == "ruby":`

**If `Ruby` were a class**, it would carry:

- methods: `aggregate_open_classes`, `collect_classes`, `extract_superclasses`, `find_method_name`, `is_function_node`, `name_extractor`
- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `cpp`

- **Total surface area**: 10 data references + 11 behaviour references = 21 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_cpp_find_function_identifier` (ccx.py:226)
- `_cpp_is_destructor` (ccx.py:278)
- `_cpp_name_extractor` (ccx.py:292)
- `_cpp_find_function_identifier` (npath.py:155)
- `_cpp_is_destructor` (npath.py:201)
- `_cpp_name_extractor` (npath.py:213)
- `_cpp_find_function_identifier` (halstead.py:162)
- `_cpp_is_destructor` (halstead.py:202)
- `_cpp_name_extractor` (halstead.py:214)
- `_extract_cpp_superclasses` (ck.py:218)
- … and 1 more

**Data (registry / config / dict-key occurrences):**

- ccx.py:697 — `"cpp": _LangConfig(`
- ccx.py:744 — `"cpp": ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],`
- npath.py:504 — `"cpp": _NpathLangConfig(`
- npath.py:538 — `"cpp": ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],`
- halstead.py:570 — `"cpp": _HalsteadLangConfig(`
- halstead.py:630 — `"cpp": ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],`
- ck.py:820 — `"cpp": _CkLangConfig(`
- ck.py:855 — `"cpp": ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],`
- ck.py:957 — `if lang == "cpp":`
- ck.py:1000 — `if ci.language == "cpp":`

**If `Cpp` were a class**, it would carry:

- methods: `collect_outofline_methods`, `extract_superclasses`, `find_function_identifier`, `is_destructor`, `name_extractor`
- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `julia`

- **Total surface area**: 6 data references + 9 behaviour references = 15 occurrences
- **Files touched**: 3 (ccx.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_julia_find_call` (ccx.py:105)
- `_julia_name_extractor` (ccx.py:130)
- `_julia_is_function_node` (ccx.py:164)
- `_julia_find_call` (npath.py:73)
- `_julia_name_extractor` (npath.py:93)
- `_julia_is_function_node` (npath.py:114)
- `_julia_find_call` (halstead.py:80)
- `_julia_name_extractor` (halstead.py:100)
- `_julia_is_function_node` (halstead.py:121)

**Data (registry / config / dict-key occurrences):**

- ccx.py:611 — `"julia": _LangConfig(`
- ccx.py:742 — `"julia": ["**/*.jl"],`
- npath.py:433 — `"julia": _NpathLangConfig(`
- npath.py:536 — `"julia": ["**/*.jl"],`
- halstead.py:462 — `"julia": _HalsteadLangConfig(`
- halstead.py:628 — `"julia": ["**/*.jl"],`

**If `Julia` were a class**, it would carry:

- methods: `find_call`, `is_function_node`, `name_extractor`
- fields / state: per-entity entries in 3 different registry/config dicts

### Entity: `c`

- **Total surface area**: 6 data references + 6 behaviour references = 12 occurrences
- **Files touched**: 3 (ccx.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_c_find_function_identifier` (ccx.py:178)
- `_c_name_extractor` (ccx.py:210)
- `_c_find_function_identifier` (npath.py:123)
- `_c_name_extractor` (npath.py:145)
- `_c_find_function_identifier` (halstead.py:130)
- `_c_name_extractor` (halstead.py:152)

**Data (registry / config / dict-key occurrences):**

- ccx.py:641 — `"c": _LangConfig(`
- ccx.py:743 — `"c": ["**/*.c", "**/*.h"],`
- npath.py:457 — `"c": _NpathLangConfig(`
- npath.py:537 — `"c": ["**/*.c", "**/*.h"],`
- halstead.py:496 — `"c": _HalsteadLangConfig(`
- halstead.py:629 — `"c": ["**/*.c", "**/*.h"],`

**If `C` were a class**, it would carry:

- methods: `find_function_identifier`, `name_extractor`
- fields / state: per-entity entries in 3 different registry/config dicts

### Entity: `go`

- **Total surface area**: 9 data references + 3 behaviour references = 12 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_collect_go_classes` (ck.py:433)
- `_extract_go_embedded` (ck.py:491)
- `_extract_go_receiver_type` (ck.py:511)

**Data (registry / config / dict-key occurrences):**

- ccx.py:67 — `languages: dict[str, int]          # {"python": 142, "go": 37}`
- ccx.py:498 — `"go": _LangConfig(`
- ccx.py:738 — `"go": ["**/*.go"],`
- npath.py:360 — `"go": _NpathLangConfig(`
- npath.py:532 — `"go": ["**/*.go"],`
- halstead.py:359 — `"go": _HalsteadLangConfig(`
- halstead.py:624 — `"go": ["**/*.go"],`
- ck.py:800 — `"go": _CkLangConfig(`
- ck.py:851 — `"go": ["**/*.go"],`

**If `Go` were a class**, it would carry:

- methods: `collect_classes`, `extract_embedded`, `extract_receiver_type`
- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `python`

- **Total surface area**: 9 data references + 2 behaviour references = 11 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_python_bool_op` (ccx.py:858)
- `_extract_python_superclasses` (ck.py:149)

**Data (registry / config / dict-key occurrences):**

- ccx.py:67 — `languages: dict[str, int]          # {"python": 142, "go": 37}`
- ccx.py:395 — `"python": _LangConfig(`
- ccx.py:735 — `"python": ["**/*.py"],`
- npath.py:309 — `"python": _NpathLangConfig(`
- npath.py:529 — `"python": ["**/*.py"],`
- halstead.py:289 — `"python": _HalsteadLangConfig(`
- halstead.py:621 — `"python": ["**/*.py"],`
- ck.py:757 — `"python": _CkLangConfig(`
- ck.py:848 — `"python": ["**/*.py"],`

**If `Python` were a class**, it would carry:

- methods: `bool_op`, `extract_superclasses`
- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `csharp`

- **Total surface area**: 8 data references + 2 behaviour references = 10 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_extract_csharp_superclasses` (ck.py:163)
- `_extract_csharp_superclasses` (ck.py:163)

**Data (registry / config / dict-key occurrences):**

- ccx.py:584 — `"c_sharp": _LangConfig(`
- ccx.py:741 — `"c_sharp": ["**/*.cs"],`
- npath.py:412 — `"c_sharp": _NpathLangConfig(`
- npath.py:535 — `"c_sharp": ["**/*.cs"],`
- halstead.py:433 — `"c_sharp": _HalsteadLangConfig(`
- halstead.py:627 — `"c_sharp": ["**/*.cs"],`
- ck.py:773 — `"c_sharp": _CkLangConfig(`
- ck.py:854 — `"c_sharp": ["**/*.cs"],`

**If `Csharp` were a class**, it would carry:

- methods: `extract_superclasses`
- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `java`

- **Total surface area**: 8 data references + 1 behaviour references = 9 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_extract_java_superclasses` (ck.py:174)

**Data (registry / config / dict-key occurrences):**

- ccx.py:549 — `"java": _LangConfig(`
- ccx.py:740 — `"java": ["**/*.java"],`
- npath.py:390 — `"java": _NpathLangConfig(`
- npath.py:534 — `"java": ["**/*.java"],`
- halstead.py:403 — `"java": _HalsteadLangConfig(`
- halstead.py:626 — `"java": ["**/*.java"],`
- ck.py:765 — `"java": _CkLangConfig(`
- ck.py:853 — `"java": ["**/*.java"],`

**If `Java` were a class**, it would carry:

- methods: `extract_superclasses`
- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `rust`

- **Total surface area**: 8 data references + 1 behaviour references = 9 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Behaviour (functions tagged with this entity):**

- `_collect_rust_classes` (ck.py:534)

**Data (registry / config / dict-key occurrences):**

- ccx.py:526 — `"rust": _LangConfig(`
- ccx.py:739 — `"rust": ["**/*.rs"],`
- npath.py:375 — `"rust": _NpathLangConfig(`
- npath.py:533 — `"rust": ["**/*.rs"],`
- halstead.py:382 — `"rust": _HalsteadLangConfig(`
- halstead.py:625 — `"rust": ["**/*.rs"],`
- ck.py:810 — `"rust": _CkLangConfig(`
- ck.py:852 — `"rust": ["**/*.rs"],`

**If `Rust` were a class**, it would carry:

- methods: `collect_classes`
- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `c_sharp`

- **Total surface area**: 8 data references + 0 behaviour references = 8 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Data (registry / config / dict-key occurrences):**

- ccx.py:584 — `"c_sharp": _LangConfig(`
- ccx.py:741 — `"c_sharp": ["**/*.cs"],`
- npath.py:412 — `"c_sharp": _NpathLangConfig(`
- npath.py:535 — `"c_sharp": ["**/*.cs"],`
- halstead.py:433 — `"c_sharp": _HalsteadLangConfig(`
- halstead.py:627 — `"c_sharp": ["**/*.cs"],`
- ck.py:773 — `"c_sharp": _CkLangConfig(`
- ck.py:854 — `"c_sharp": ["**/*.cs"],`

**If `C_sharp` were a class**, it would carry:

- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `javascript`

- **Total surface area**: 8 data references + 0 behaviour references = 8 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Data (registry / config / dict-key occurrences):**

- ccx.py:424 — `"javascript": _LangConfig(`
- ccx.py:736 — `"javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],`
- npath.py:322 — `"javascript": _NpathLangConfig(`
- npath.py:530 — `"javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],`
- halstead.py:307 — `"javascript": _HalsteadLangConfig(`
- halstead.py:622 — `"javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],`
- ck.py:792 — `"javascript": _CkLangConfig(`
- ck.py:849 — `"javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],`

**If `Javascript` were a class**, it would carry:

- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `typescript`

- **Total surface area**: 8 data references + 0 behaviour references = 8 occurrences
- **Files touched**: 4 (ccx.py, ck.py, halstead.py, npath.py)

**Data (registry / config / dict-key occurrences):**

- ccx.py:461 — `"typescript": _LangConfig(`
- ccx.py:737 — `"typescript": ["**/*.ts", "**/*.tsx"],`
- npath.py:341 — `"typescript": _NpathLangConfig(`
- npath.py:531 — `"typescript": ["**/*.ts", "**/*.tsx"],`
- halstead.py:332 — `"typescript": _HalsteadLangConfig(`
- halstead.py:623 — `"typescript": ["**/*.ts", "**/*.tsx"],`
- ck.py:784 — `"typescript": _CkLangConfig(`
- ck.py:850 — `"typescript": ["**/*.ts", "**/*.tsx"],`

**If `Typescript` were a class**, it would carry:

- fields / state: per-entity entries in 4 different registry/config dicts

### Entity: `js`

- **Total surface area**: 0 data references + 1 behaviour references = 1 occurrences
- **Files touched**: 1 (ck.py)

**Behaviour (functions tagged with this entity):**

- `_extract_js_superclasses` (ck.py:207)

**If `Js` were a class**, it would carry:

- methods: `extract_superclasses`
- fields / state: per-entity entries in 0 different registry/config dicts

### Entity: `ts`

- **Total surface area**: 0 data references + 1 behaviour references = 1 occurrences
- **Files touched**: 1 (ck.py)

**Behaviour (functions tagged with this entity):**

- `_extract_ts_superclasses` (ck.py:195)

**If `Ts` were a class**, it would carry:

- methods: `extract_superclasses`
- fields / state: per-entity entries in 0 different registry/config dicts

