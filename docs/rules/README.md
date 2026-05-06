# slop rules

slop rules are organised into three suites separated by measurement substrate, not by how serious a violation feels. Each suite has its own README; each leaf rule has its own page.

| Suite | Measures | Substrate |
|---|---|---|
| [`structural`](structural/README.md) | Shape and graph risk | AST, control flow, import graph, inheritance graph, package graph, git churn |
| [`information`](information/README.md) | Information density and readability proxies | operator/operand counts, literal frequencies, comment markers |
| [`lexical`](lexical/README.md) | Vocabulary discipline | identifier strings, AST scope names |
| [`composition`](composition/README.md) | Missing namespace / receiver candidates | function definitions, identifier-token alphabets, first-parameter clusters |

Rule names are fully qualified and dot-separated. The hierarchy under `structural.*` reflects the measurement target:

- `structural.complexity.*` — per-function control-flow metrics
- `structural.class.*` — class-level CK metrics, including `structural.class.inheritance.*`
- `structural.types.*` — type-discipline rules
- `structural.{hotspots,packages,deps,...}` — single-rule structural categories

## Full rule index

### structural

| Rule | Default | Page |
|---|---|---|
| `structural.complexity.cyclomatic` | CCX > 10 | [→](structural/complexity/cyclomatic.md) |
| `structural.complexity.cognitive` | CogC > 15 | [→](structural/complexity/cognitive.md) |
| `structural.complexity.npath` | NPath > 400 | [→](structural/complexity/npath.md) |
| `structural.class.complexity` | WMC > 40 | [→](structural/class/complexity.md) |
| `structural.class.coupling` | CBO > 8 | [→](structural/class/coupling.md) |
| `structural.class.inheritance.depth` | DIT > 4 | [→](structural/class/inheritance/depth.md) |
| `structural.class.inheritance.children` | NOC > 10 | [→](structural/class/inheritance/children.md) |
| `structural.hotspots` | 14d window | [→](structural/hotspots.md) |
| `structural.packages` | D' > 0.7 | [→](structural/packages.md) |
| `structural.deps` | any cycle | [→](structural/deps.md) |
| `structural.local_imports` | any (warning) | [→](structural/local_imports.md) |
| `structural.redundancy` | ≥ 3 shared | [→](structural/redundancy.md) |
| `structural.types.sentinels` | ≤ 8 values | [→](structural/types/sentinels.md) |
| `structural.types.hidden_mutators` | any mutation | [→](structural/types/hidden_mutators.md) |
| `structural.types.escape_hatches` | > 30% | [→](structural/types/escape_hatches.md) |
| `structural.duplication` | > 5% | [→](structural/duplication.md) |
| `structural.god_module` | > 20 | [→](structural/god_module.md) |
| `structural.orphans` | disabled | [→](structural/orphans.md) |

### information

| Rule | Default | Page |
|---|---|---|
| `information.volume` | V > 1500 | [→](information/volume.md) |
| `information.difficulty` | D > 30 | [→](information/difficulty.md) |
| `information.magic_literals` | > 3 | [→](information/magic_literals.md) |
| `information.section_comments` | > 2 | [→](information/section_comments.md) |

### lexical

| Rule | Default | Page |
|---|---|---|
| `lexical.stutter.namespaces` | ≥ 2 tokens | [→](lexical/stutter.md) |
| `lexical.stutter.callers` | ≥ 2 tokens | [→](lexical/stutter.md) |
| `lexical.stutter.identifiers` | ≥ 2 tokens | [→](lexical/stutter.md) |
| `lexical.verbosity` | mean > 3.0 | [→](lexical/verbosity.md) |
| `lexical.tersity` | > 50% | [→](lexical/tersity.md) |
| `lexical.name_verbosity` | > 3 tokens | [→](lexical/name_verbosity.md) |
| `lexical.numbered_variants` | any match | [→](lexical/numbered_variants.md) |
| `lexical.weasel_words` | banlist match | [→](lexical/weasel_words.md) |
| `lexical.type_tag_suffixes` | suffix matches type | [→](lexical/type_tag_suffixes.md) |
| `lexical.boilerplate_docstrings` | content ⊆ name | [→](lexical/boilerplate_docstrings.md) |
| `lexical.identifier_singletons` | > 60% singleton | [→](lexical/identifier_singletons.md) |

### composition

| Rule | Default | Page |
|---|---|---|
| `composition.affix_polymorphism` | ≥ 3 alphabet × ≥ 2 ops | [→](composition/affix_polymorphism.md) |
| `composition.first_parameter_drift` | ≥ 3 fns sharing param | [→](composition/first_parameter_drift.md) |

## Naming principle

Suite names describe **what is measured**, not the **technique used**. `structural` is named after its subject (program structure); `information` is named after its subject (information content); `lexical` is named after its subject (vocabulary).

Subcategories follow the same principle: `structural.complexity` is a category of structural rules that measures complexity, not a category of complexity rules that happen to be structural.

## Default severity and exit codes

- `severity = "error"` (default for established rules) — violation fails the lint run, exit code 1.
- `severity = "warning"` (default for advisory rules) — violation reports but does not fail.

Adopt slop gradually by setting everything to `warning` first, reviewing for a week, then promoting rules to `error` one at a time.

## Configuration

Configuration is per-rule in `.slop.toml` (or `[tool.slop]` in `pyproject.toml`):

```toml
[rules.structural.complexity]
cyclomatic_threshold = 10

[rules.lexical.verbosity]
max_mean_tokens = 3.0
```

`enabled` and `severity` may also be set on any prefix table — `[rules.lexical]`, `[rules.structural.class]`, `[rules.structural]` — and they propagate to every rule under that prefix. More specific tables override broader ones.

```toml
# disable an entire suite
[rules.lexical]
enabled = false

# disable a group within a suite
[rules.structural.class]
enabled = false
```

See [`docs/CONFIG.md`](../CONFIG.md) for the full configuration reference, profiles (`default`, `lax`, `strict`), waivers, and severity levels.

## Legacy rule names

Pre-0.9.0 rule names (`complexity.*`, `halstead.*`, `npath`, `hotspots`, `class.*`, ...) and their matching `[rules.<old>]` TOML tables are still accepted via a compatibility shim that translates to the canonical names at config-load time. The shim is scheduled for removal in 1.1.0. See `CHANGELOG.md` for the full mapping.
