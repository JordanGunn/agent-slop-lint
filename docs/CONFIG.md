# Configuration Reference

slop reads config from `.slop.toml`, or a `[tool.slop]` table in `pyproject.toml`. It walks
**upward from `--root`** for the nearest of those (a `pyproject.toml` without `[tool.slop]`
is skipped, so a sub-project file doesn't mask a repo-root `.slop.toml`). `slop init` writes
a commented starter; `slop schema` prints the exact shape, generated from the rule registry
so it cannot drift from the rules it describes.

slop is built to be tuned, not disabled: prefer adjusting a threshold or exempting a
specific scope over turning a rule off wholesale.

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
  govern output volume, not the verdict. Configurable even for observations.
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

## Exit codes

`0` clean · `1` any error-severity verdict · `2` error (bad config, or a nonexistent /
source-free `--root`).

## What changed from v1.x

There are no `default` / `lax` / `strict` **profiles** and no `[[waivers]]` array. Tune
thresholds directly and exempt via `[ignore]`. The config file holds rule settings only —
the scan target is the CLI's `--root`, not a config key.
