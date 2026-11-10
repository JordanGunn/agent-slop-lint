# Configuration Reference

slop reads config from `.slop.toml`, or a `[tool.slop]` table in `pyproject.toml`. It walks
**upward from `--root`** for the nearest of those (a `pyproject.toml` without `[tool.slop]`
is skipped, so a sub-project file doesn't mask a repo-root `.slop.toml`). `slop init` writes
a commented starter; `slop schema` prints the exact shape, generated from the rule registry
so it cannot drift from the rules it describes.

A config file may contain only three top-level keys: `exclude`, `languages` and `rules`.
Any other top-level key (including the removed `[ignore]` table) is a load error, so `lint`
and `check` exit 2 rather than silently ignoring it. The read-only commands (`find`, `tree`,
`lexicon`, `deps`, `vocab`, `shape`) read only `exclude` and `languages`.

## `exclude` — files slop does not read

```toml
exclude = ["tests/**", "**/vendor/**"]
```

Globs over POSIX paths **relative to the directory holding the config file** (`*` crosses
`/`, so `tests/**` covers everything beneath `tests/`; a leading `**/` also matches the top
level). Excluded files are never carved, so they appear in no command: `lint`, `find`,
`tree`, `lexicon`, `vocab` and `shape` all see the same corpus.

## `languages` — which languages slop reads

```toml
languages = ["python", "typescript"]
```

Language ids to carve; omitted or empty means every supported language (`c`, `c_sharp`,
`cpp`, `go`, `java`, `javascript`, `julia`, `python`, `ruby`, `rust`, `typescript`). An
unknown id is a load error that lists the supported ones. Like `exclude`, it applies to every
command.

## `[rules]` — per-rule settings

Each rule is configured under `[rules."<name>"]` (the quotes matter: rule names contain
dots). Three keys:

```toml
[rules."complexity.cyclomatic"]
enabled = true                 # default true (class.cohesion defaults to false)
thresholds.callable = 12       # keyed by the rule's declared ALTITUDE, not a flat number

[rules."structure.duplication"]
params.min_leaf_nodes = 20     # a rule-specific noise floor
```

- **`enabled`** turns the rule on or off.
- **`thresholds`** are keyed by altitude label (`callable` / `class` / `module` / `package`
  / `corpus`), the scope the rule measures at. A violation is reported when the measure is
  **strictly greater** than the limit. A threshold keyed to an altitude the rule does
  **not** declare is a load error, not a silent no-op: if slop accepts your config, the rule
  is applying it. `slop rules` shows each rule's altitude; `slop schema` shows its threshold
  keys and defaults.
- **`params`** (`params.<key> = <value>`) are noise floors. A param the rule does not
  declare is a load error, and `slop schema` lists each rule's params. They must sit in the
  `params` table: a bare `<key> = <value>` on a rule is also an error.

Rule tables accept no other keys.

## Suppressing a violation

Suppression is inline, on the line a violation is reported at, in any comment syntax:

```python
def legacy_parse(x):  # slop: ignore[complexity.cyclomatic]
```

- `slop: ignore` drops every violation reported on that line.
- `slop: ignore[a, b]` drops only those rules. A family prefix covers its rules:
  `slop: ignore[complexity]` covers `complexity.cyclomatic`, `complexity.cognitive` and
  `complexity.combinatorial`.

The reported line is the line of the definition (`path:line` in the output). To exempt a
whole file or directory from every command, use `exclude`.

## Exit codes

`0` no violations · `1` at least one violation · `2` error (bad config, or a nonexistent /
source-free `--root`).

## What changed from earlier versions

There are no profiles, no `[[waivers]]` array and no scope-keyed
`[ignore]` table, and rules carry no per-rule level. Tune thresholds directly and suppress inline. The scan target itself is
the CLI's `--root`, not a config key.
