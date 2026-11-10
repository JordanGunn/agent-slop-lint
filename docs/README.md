# Documentation

slop has two layers today, and a third planned:

1. **Primitives**: read-only facts about a codebase (`find`, `tree`, `shape`, `lexicon`,
   `deps`, `vocab`, `ast`), with no thresholds.
2. **Lint**: a plain, typical linter. 12 rules, each a threshold on a well-cited measure
   (McCabe 1976 through Campbell 2018), each violation a `path:line:column: rule message`
   line. Exit 1 if there is any.
3. **Inference** (later, separate): judgement over what the checks find. It is not part of
   slop's lint.

## Use it

- [rules/README.md](rules/README.md): the 12 rules at a glance. The always-current
  reference is `slop rules` (listing) and `slop schema` (config shape); each rule's full
  rationale lives in its module docstring under `src/slop/rules/`.
- [CONFIG.md](CONFIG.md): `.slop.toml` / `[tool.slop]` (`exclude`, `languages`, per-rule
  `enabled` / `thresholds` / `params`) and inline `slop: ignore[rule]` suppression.
- Install and CLI usage are in the repo-root [README](../README.md).

## How it's built

The architecture (the Corpus › Realm › Package › Module › Class › Callable component model,
the `Structure` view, the dispatcher, the `Violation` record) is documented for
contributors in the repo-root [CLAUDE.md](../CLAUDE.md). Durable internal design docs live
under `docs/.internal/design/`; the rule model is in
[.internal/design/RULES.md](.internal/design/RULES.md).
