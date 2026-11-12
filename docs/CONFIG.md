# Configuration

slop reads `.slop.toml`, or a `[tool.slop]` table in `pyproject.toml`, from the nearest
directory at or above `--root`. `slop init` writes a commented template.

Every command loads the same config. An invalid config exits `2`.

## Keys

Only `exclude` and `rules` are accepted at the top level.

### `exclude`

```toml
exclude = ["tests/**", "**/vendor/**"]
```

Globs over POSIX paths relative to the directory holding the config file. `*` crosses `/`,
so `tests/**` covers everything beneath `tests/`. Excluded files are never read.

### `[rules.<name>]`

```toml
[rules.cyclomatic-complexity]
limit = 12

[rules.duplicate-code]
min_leaf_nodes = 20

[rules.class-cohesion]
enabled = false
```

- `enabled`: boolean, default `true` for every rule. A subjective rule (`class-cohesion`,
  `rigid-package`, `useless-package`) that is enabled reports warnings, which never exit 1.
- Options: `limit` for every rule except `import-cycle`; `duplicate-code` also takes
  `min_leaf_nodes`, and `duplicate-string` also takes `min_length`. An integer option needs an integer; `rigid-package` and
  `useless-package` take an integer or float.

An unknown rule name, option, or wrongly typed value is an error. `slop rules` lists rule
names; `slop init` shows every option and its default.

## Inline suppression

On the line a violation is reported at, in any comment syntax:

```python
def legacy_parse(x):  # slop: ignore[cyclomatic-complexity]
```

- `slop: ignore` drops every violation reported on that line.
- `slop: ignore[a, b]` drops only the rules named, by exact name.

To exempt a file or directory, use `exclude`.
