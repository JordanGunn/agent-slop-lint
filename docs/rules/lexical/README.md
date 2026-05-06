# Lexical rules

Lexical rules measure vocabulary quality. They operate on tokenized identifier streams and AST scope names. They care about the words themselves: whether they are redundant, overly wordy, or cryptic.

| Rule | Default | What it catches |
|---|---|---|
| [`lexical.stutter.namespaces`](stutter.md) | ≥ 2 tokens | Symbol stutters with module path |
| [`lexical.stutter.callers`](stutter.md) | ≥ 2 tokens | Method/attribute stutters with enclosing class |
| [`lexical.stutter.identifiers`](stutter.md) | ≥ 2 tokens | Local variable stutters with enclosing function |
| [`lexical.verbosity`](verbosity.md) | mean > 3.0 | Functions with overly verbose multi-token identifiers |
| [`lexical.tersity`](tersity.md) | > 50% | Overuse of very short (≤ 2 char) identifiers (guardrail) |
| [`lexical.name_verbosity`](name_verbosity.md) | > 3 tokens | Function/class names with too many tokens (class-without-class signal) |
| [`lexical.numbered_variants`](numbered_variants.md) | any match | Identifiers ending in disambiguator suffixes (`_1`, `_v2`, `_old`, `_new`) |
| [`lexical.weasel_words`](weasel_words.md) | banlist match | Catchall vocabulary (`Manager`, `Helper`, `Util`, `Spec`, …) |
| [`lexical.type_tag_suffixes`](type_tag_suffixes.md) | suffix matches type | Identifier suffixes that restate the type annotation |
| [`lexical.boilerplate_docstrings`](boilerplate_docstrings.md) | content ⊆ name | Docstrings that just restate the function name |
| [`lexical.identifier_singletons`](identifier_singletons.md) | > 60% singleton | Functions where most locals are write-once-read-once |

## Category properties

- **Substrate:** identifier strings, AST scope names. Splits on snake_case and CamelCase boundaries.
- **Compute profile:** fast.
- **Determinism:** full. Identical source produces identical output.
- **Failure modes:** acronym splitting edge cases, conventional short names (`i`, `j`, `k`) that are not on the allow-list, language-specific naming idioms that violate general rules.
- **Interpretation burden:** low. Every violation can be explained in one sentence.

## Why the three rules pair

`lexical.verbosity` pushes against agentic-era naming bloat — the model's tendency to produce `extracted_lidar_point_x_coordinate` when `x` would do. `lexical.tersity` is the guardrail against the opposite failure mode: over-correcting into cryptic single-letter names everywhere. `lexical.stutter` catches the third smell — names that are not too long or too short, just redundant against their enclosing context.
