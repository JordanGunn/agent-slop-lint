# Composition rules

Composition rules surface candidate abstractions hiding in flat
collections of free functions. They detect lexical and signature
patterns that suggest a missing namespace, class, or receiver — the
kind of architectural slip that happens when an agent extends a
file by adding "one more helper" instead of recognising that the
helpers form a family.

| Rule | Default | What it catches |
|---|---|---|
| [`composition.affix_polymorphism`](affix_polymorphism.md) | ≥ 3 alphabet × ≥ 2 ops | Identifiers sharing a stem with one position varying over a closed alphabet (missing namespace candidate) |
| [`composition.first_parameter_drift`](first_parameter_drift.md) | ≥ 3 functions sharing param | Free functions sharing a first-parameter name (missing receiver / class candidate) |

## Category properties

- **Substrate:** function definitions across all configured
  languages, parsed via tree-sitter. Identifier-token analysis on
  function names; first-parameter extraction from parameter lists.
- **Compute profile:** moderate. Cross-language AST walk plus
  clustering; comparable to the structural duplication rule.
- **Determinism:** full. Identical source produces identical
  output.
- **Failure modes:** false positives on third-party library types
  (`node`, `tree`, `path`) — mitigated by a configurable exempt
  list and verdict classification (strong / weak / false-positive).
- **Interpretation burden:** **high**. These rules surface
  *candidates*, not violations of an objective threshold. Acting
  on the signal is an architectural decision; the rule's job is
  to make sure the option is visible, not to coerce a refactor.

## Why these rules

Agent-written code accumulates flat function families faster than
human-written code, because each prompt extension is a local
operation that doesn't see the whole file. Over time, the file
develops a tabular structure (one helper per language, per format,
per backend) that a human author would have factored into a class
hierarchy, a strategy table, or a polymorphic interface during the
second or third addition.

These rules notice the structure that has already emerged. The
verdict — fold into a class, leave as free functions, or extract a
dispatch table — is yours.

## Empirical grounding

The detection algorithms ported from
`scripts/research/composition_poc/`. Three rounds of experiments
on slop's own kernel surface evaluated five algorithms across six
sub-agent invocations. Findings recorded in
`docs/observations/composition/01.md` and `02.md`. Methodology and
prior-art chain (Wille 1982; Caprile & Tonella 2000; Bavota et al.;
Harris 1955) are documented in
[`docs/philosophy/composition-and-lexical.md`](../../philosophy/composition-and-lexical.md).
