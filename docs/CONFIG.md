# Configuration Reference

This guide explains every configurable value in slop, what it means in practice, and when to change it. The goal is to help you tune slop to your project rather than disable it when a rule gets in the way.

slop reads config from `.slop.toml` (or `[tool.slop]` in `pyproject.toml`). Generate a starter config with `slop init`.

## A note on default thresholds

slop cites well-established metrics (McCabe, Chidamber & Kemerer, Halstead, Nejmeh, Martin, Tornhill) and most defaults match the numbers from those original sources. Three do not, and this section documents why so readers who open the cited papers can reconcile the discrepancy.

| Rule | Citation's threshold | slop default | Why slop diverges |
|---|---:|---:|---|
| `structural.class.complexity` (WMC) | ~50 (1990s industry convention) | 40 | Contemporary OO advice (Fowler, Martin) treats classes with more than a handful of responsibilities as refactor candidates. 40 aligns with modern practice and catches god-class drift earlier. |
| `information.volume` | ~1000 (SonarSource-style) | 1500 | The 1000 ceiling flags legitimate orchestration code (formatters, dispatchers, fused pipelines) that are not actually rot. 1500 still flags the pathological case where three responsibilities fused into one function, without penalising honest breadth-heavy code. |
| `structural.complexity.npath` | 200 (Nejmeh 1988) | 400 | Nejmeh's 200 was calibrated on pre-OO C code at AT&T Bell Labs in 1988. Modern CLI dispatch patterns (click, argparse, cobra) routinely produce honest `main` functions at NPath 256-512 because each `if args.command == "X"` doubles the count. 400 raises the floor above typical dispatch while still flagging the 10-sequential-if combinatorial explosion (NPath=1024). |

Every other rule's default matches the cited source.

## Scoped waivers

Do not lower a global threshold just because one parser, state machine,
generated-adjacent file, or compatibility layer is legitimately more complex
than the rest of the project. Use a waiver instead.

A waiver is a bounded exception. slop still analyzes the code and still prints
the finding, but a matching finding does not fail the run while it remains
inside the waiver's local ceiling.

```toml
[[waivers]]
id = "parser-npath"
path = "src/parser/**"
rule = "structural.complexity.npath"
allow_up_to = 1200
reason = "Parser branch shape mirrors grammar alternatives."
expires = "2026-09-01"
```

Required fields:

| Field | Meaning |
|---|---|
| `id` | Stable identifier shown in output and JSON. Must be unique. |
| `path` | Glob matched against repo-relative violation paths. |
| `rule` | One rule name or glob pattern, for example `"structural.complexity.npath"` or `"structural.complexity.cognitive"`. |
| `reason` | Human-readable rationale. Required so exceptions are reviewable. |

Optional fields:

| Field | Meaning |
|---|---|
| `allow_up_to` | Local ceiling for numeric findings. If the measured value exceeds this number, the finding fails normally. |
| `expires` | ISO date (`YYYY-MM-DD`). Expired waivers no longer apply. |

Waivers are intentionally different from `exclude`.

- `exclude` means "do not analyze this path."
- `waivers` means "analyze this path, show matching findings, but do not fail
  while the finding stays within a documented exception."

Prefer `allow_up_to` for complexity, NPath, Halstead, class, package, and
hotspot findings. An unbounded waiver is allowed for non-numeric cases such as
dependency cycles, but it should be rare because it can hide growth inside the
exception boundary.

Each waiver has exactly one local ceiling. If one path needs exceptions for
multiple metrics, write multiple waiver entries. Do not reuse one number across
metrics with different scales.

```toml
[[waivers]]
id = "parser-npath"
path = "src/parser/**"
rule = "structural.complexity.npath"
allow_up_to = 1200
reason = "Parser branch shape mirrors grammar alternatives."

[[waivers]]
id = "parser-cognitive"
path = "src/parser/**"
rule = "structural.complexity.cognitive"
allow_up_to = 30
reason = "Parser branch shape mirrors grammar alternatives."
```

Waived findings appear in human output under a `waived` block and in JSON under
`waived_violations`. They are not counted as failing violations.

Human output:

```text
structural.complexity
  npath waived
    ⚠ src/parser/grammar.py:88 parse_expr — NPath 914 exceeds 400 (waived by parser-npath)
      reason: Parser branch shape mirrors grammar alternatives.

  1 waived, 42 checked

────────────────────────────────────────
1 waived | 1 rule checked | PASS
```

JSON output keeps failing and waived findings separate:

```json
{
  "rules": {
    "structural.complexity.npath": {
      "violations": [],
      "waived_violations": [
        {
          "rule": "structural.complexity.npath",
          "file": "src/parser/grammar.py",
          "value": 914,
          "threshold": 400,
          "metadata": {
            "waiver": {
              "id": "parser-npath",
              "reason": "Parser branch shape mirrors grammar alternatives.",
              "allow_up_to": 1200,
              "expires": null
            }
          }
        }
      ]
    }
  }
}
```

Expired waivers and findings above `allow_up_to` fail normally. That makes a
waiver a ceiling, not an ignore.

## Rule reference

Per-rule pages — what each rule measures, default thresholds, when to raise, when to lower, when to disable — live under [`docs/rules/`](rules/README.md). Each leaf rule has its own page; each suite and group has a README.

| Suite | Index |
|---|---|
| `structural.*` | [`docs/rules/structural/`](rules/structural/README.md) |
| `information.*` | [`docs/rules/information/`](rules/information/README.md) |
| `lexical.*` | [`docs/rules/lexical/`](rules/lexical/README.md) |

The remaining sections of this document cover cross-rule configuration: profiles, when to disable a rule, severity levels, and legacy name handling.

## Profiles

Generate a profile directly with `slop init`:

```bash
slop init              # default — balanced for most projects
slop init lax          # lax — legacy codebases or gradual adoption
slop init strict       # strict — greenfield or quality-focused teams
```

Or copy one of the configs below into your `.slop.toml` manually.

> The snippets in this section are **abridged** — they show only the rules whose thresholds vary across profiles. Rules whose thresholds are constant across all three profiles (every `lexical.*` rule, `structural.types.*`, `structural.duplication`, `structural.god_module`, `structural.local_imports`, `structural.redundancy`, `information.magic_literals`, `information.section_comments`) are omitted for brevity. Run `slop init <profile>` for the full generated config.

### Default — balanced for most projects

```toml
[rules.structural.complexity]
cyclomatic_threshold = 10
cognitive_threshold = 15
npath_threshold = 400

[rules.structural.class.complexity]
threshold = 40

[rules.structural.class.coupling]
threshold = 8

[rules.structural.class.inheritance.depth]
threshold = 4

[rules.structural.class.inheritance.children]
threshold = 10

[rules.structural.hotspots]
since = "14 days ago"
min_commits = 2
fail_on_quadrant = ["hotspot"]

[rules.structural.packages]
max_distance = 0.7
severity = "warning"

[rules.structural.deps]
fail_on_cycles = true

[rules.structural.orphans]
enabled = false

[rules.information.volume]
threshold = 1500

[rules.information.difficulty]
threshold = 30
```

### Lax — for legacy codebases or gradual adoption

Start here if the default profile produces too many violations to act on. Tighten over time.

```toml
[rules.structural.complexity]
cyclomatic_threshold = 20
cognitive_threshold = 25
npath_threshold = 1000

[rules.structural.class.complexity]
threshold = 80

[rules.structural.class.coupling]
threshold = 15

[rules.structural.class.inheritance.depth]
threshold = 6

[rules.structural.class.inheritance.children]
threshold = 20

[rules.structural.hotspots]
since = "90 days ago"
min_commits = 3
fail_on_quadrant = ["hotspot"]

[rules.structural.packages]
max_distance = 0.85
severity = "warning"

[rules.structural.deps]
fail_on_cycles = true

[rules.structural.orphans]
enabled = false

[rules.information.volume]
threshold = 3000

[rules.information.difficulty]
threshold = 50
```

### Strict — for greenfield projects or quality-focused teams

Catches problems before they compound. Expect some friction in the first week as existing code is brought into compliance.

```toml
[rules.structural.complexity]
cyclomatic_threshold = 6
cognitive_threshold = 10
npath_threshold = 100

[rules.structural.class.complexity]
threshold = 30

[rules.structural.class.coupling]
threshold = 5

[rules.structural.class.inheritance.depth]
threshold = 3

[rules.structural.class.inheritance.children]
threshold = 7

[rules.structural.hotspots]
since = "7 days ago"
min_commits = 1
fail_on_quadrant = ["hotspot", "churning_simple"]

[rules.structural.packages]
max_distance = 0.5
severity = "error"

[rules.structural.deps]
fail_on_cycles = true

[rules.structural.orphans]
enabled = true
min_confidence = "high"
severity = "warning"

[rules.information.volume]
threshold = 500

[rules.information.difficulty]
threshold = 20
```

## Disabling rules, groups, and suites

Any prefix in the rule taxonomy can be toggled in one place. `enabled` and `severity` set on an intermediate `[rules.<prefix>]` table propagate to every rule whose canonical name starts with that prefix; a more specific table always wins over a broader one.

```toml
# disable an entire suite
[rules.lexical]
enabled = false

# disable a group
[rules.structural.class]
enabled = false

# disable one rule
[rules.structural.orphans]
enabled = false

# disable a suite, but keep one rule on
[rules.structural]
enabled = false

[rules.structural.complexity]
enabled = true
```

Only `enabled` and `severity` propagate from prefix tables. Threshold keys (`cyclomatic_threshold`, `max_distance`, …) only have meaning at the leaf rule's own table.

### Per-rule disable guidance

Disabling a rule is a legitimate choice in specific contexts. The table below helps you decide rather than guess.

| Rule | Disable when | Keep enabled when |
|---|---|---|
| `structural.class.complexity` | No classes in your codebase (functional style, scripting) | Any OOP codebase |
| `structural.hotspots` | No git history available, or running in a shallow-cloned CI without `fetch-depth: 0` | Any git repo with history |
| `structural.packages` | Single-package project (metric ill-defined) | Multi-package projects in any supported language |
| `structural.deps` | Very early prototype with intentionally fluid boundaries | Any project past the prototype stage |
| `structural.orphans` | Always off as a CI gate. Enable for periodic cleanup audits only. | Never as a permanent gate — false positive rate is too high |
| `structural.class.coupling` | No classes (functional, scripting) | Any OOP codebase |
| `structural.class.inheritance.depth` | No inheritance used (composition-only architecture) | Any codebase using class hierarchies |
| `structural.class.inheritance.children` | Plugin architectures where many subclasses are by design | Standard OOP codebases |
| `structural.complexity.cyclomatic` | Never — this is the most fundamental complexity metric | Always |
| `structural.complexity.cognitive` | Never — this catches readability problems CCX misses | Always |

**The two rules you should never disable** are `structural.complexity.cyclomatic` and `structural.complexity.cognitive`. If they're too noisy, raise the thresholds — don't turn them off. Complexity that goes unmeasured always grows.

## Severity levels

Each rule has a `severity` setting:

| Severity | Exit code | Meaning |
|---|---|---|
| `"error"` | 1 (fail) | Violation fails the lint run. Use for hard gates. |
| `"warning"` | 0 (pass) | Violation is reported but doesn't fail. Use for advisory rules or gradual adoption. |

To adopt slop gradually, start with everything set to `severity = "warning"`, review the output for a week, then promote rules to `"error"` one at a time.

```toml
# Gradual adoption example — everything advisory at first
[rules.structural.complexity]
severity = "warning"

[rules.structural.hotspots]
severity = "warning"

[rules.structural.class]
severity = "warning"
```

## Legacy rule names

Pre-0.9.0 rule names (`complexity.cyclomatic`, `halstead.volume`, `npath`,
`hotspots`, `packages`, `deps`, `orphans`, `class.coupling`, ...) and their
matching `[rules.<old>]` TOML tables are still accepted. They are translated
to canonical form at config-load time and trigger a single consolidated
deprecation warning to stderr. The compatibility shim is scheduled for
removal in 1.1.0; migrate when convenient. See the table in `CHANGELOG.md`
for the full mapping.
