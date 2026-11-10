# Configuration Reference

slop reads config from `.slop.toml`, or a `[tool.slop]` table in `pyproject.toml`. It walks
**upward from `--root`** for the nearest of those (a `pyproject.toml` without `[tool.slop]`
is skipped, so a sub-project file doesn't mask a repo-root `.slop.toml`). `slop init` writes
a commented starter; `slop schema` prints the exact shape, generated from the rule registry
so it cannot drift from the rules it describes.

slop is built to be tuned, not disabled: prefer adjusting a threshold or exempting a
specific scope over turning a rule off wholesale.

## `exclude` — files slop does not read

```toml
exclude = ["tests/**", "**/vendor/**"]
```

Globs over POSIX paths **relative to the directory holding the config file** (`*` crosses
`/`, so `tests/**` covers everything beneath `tests/`; a leading `**/` also matches the top
level). Excluded files are never carved, so they appear in no command: `lint`, `find`,
`tree`, `lexicon`, `vocab`, `shape` and `hotspots` all see the same corpus. The read-only
commands read only `exclude` and `languages` from the config, so a stale `[rules]` section
cannot stop them.

## `languages` — which languages slop reads

```toml
languages = ["python", "typescript"]
```

Language ids to carve; omitted or empty means every supported language (`c`, `c_sharp`,
`cpp`, `go`, `java`, `javascript`, `julia`, `python`, `ruby`, `rust`, `typescript`). An
unknown id is a load error that lists the supported ones. Like `exclude`, it applies to every
command, and the read-only commands read it from the config (see below).

## `[rules]` — per-rule settings

Each rule is configured under `[rules."<name>"]` (the quotes matter — rule names contain
dots). Four keys:

```toml
[rules."complexity.cyclomatic"]
enabled = true                 # default true
severity = "error"             # error | warning | info  (verdict rules only)
thresholds.callable = 12       # keyed by the rule's declared ALTITUDE, not a flat number
```

- **`thresholds`** are keyed by altitude label (`callable` / `class` / `module` / `package`
  / `corpus`) — the scope the rule measures at. A threshold keyed to an altitude the rule
  does **not** declare is a *load error*, not a silent no-op. This is the structural cure
  for the legacy "config keyed wrong, rule silently checks nothing" failure: if slop
  accepts your config, the rule is actually applying it. `slop rules` shows each rule's
  altitude; `slop schema` shows its threshold keys.
- **`params`** (`params.<key> = <value>`) are noise floors and significance gates — they
  govern output volume, not the verdict. Configurable even for observations. A param the
  rule does not declare is a *load error* (a misspelt name would otherwise do nothing), and
  `slop schema` lists each rule's params. They must sit in the `params` table: a bare
  `<key> = <value>` on a rule is also an error.
- **`severity`** applies to verdict rules. Observation rules pin `info` and ignore it (an
  observation never gates the build). A `REVIEW` verdict caps at `warning`.

## `[ignore]` — scope-keyed exemptions

Suppress a finding by naming the unit it judges, keyed by that unit's scope:

```toml
[ignore]
functions = ["legacy_parse"]
classes   = ["LegacyAdapter"]
modules   = ["vendored_shim"]
packages  = ["thirdparty"]
```

A finding is suppressed when its component's qualified name (or leaf name) appears in the
list for its scope kind. The win over path-level waivers is **scope precision** —
`classes = ["Lexicon"]` exempts the class-level finding on `Lexicon` without blinding its
methods' callable-level findings. An unknown scope key (e.g. `any`) is a load error.
Suppression is silent; the exemption is auditable in config, not the output. There is no
expiry or allowance ceiling.

A plain entry exempts **every** unit of that name, so `classes = ["Params"]` silences all
classes called `Params`. To exempt one, write `path::name`:

```toml
[ignore]
classes = ["transform/grid/params.py::Params"]
```

The path matches the end of the unit's source path at a `/` boundary (`params.py` would also
match `grid/params.py`, but not `myparams.py`); the name is the qualified or leaf name.

## Exit codes

`0` clean · `1` any error-severity verdict · `2` error (bad config, or a nonexistent /
source-free `--root`).

## What changed from v1.x

There are no `default` / `lax` / `strict` **profiles** and no `[[waivers]]` array. Tune
thresholds directly and exempt via `[ignore]`. The config file holds rule settings and the
`exclude` list only — the scan target is the CLI's `--root`, not a config key.
