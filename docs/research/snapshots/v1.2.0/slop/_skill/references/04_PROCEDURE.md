---
description: How to run slop and interpret the JSON output.
index:
  - Invocation
  - Config bootstrap
  - Interpreting results
  - Reporting to the user
---

# Procedure

## Invocation

```bash
# Full lint (all enabled rules)
slop lint --root <path> --output json

# One category
slop check structural.complexity --root <path> --output json

# One rule
slop check structural.class.coupling --root <path> --output json
```

Always use `--output json`. Never parse human output.

## Config bootstrap

Before the first run in a project, check if `.slop.toml` or a
`[tool.slop]` section in `pyproject.toml` exists. If neither exists:

```bash
cd <project_root>
slop init
```

This generates `.slop.toml` with annotated defaults. Mention it to the
user once: "Generated .slop.toml with default thresholds." Then proceed.

## Interpreting results

The JSON structure:

```json
{
  "summary": {
    "violation_count": 12,
    "advisory_count": 0,
    "rules_checked": 9,
    "result": "fail"
  },
  "rules": {
    "<rule_name>": {
      "status": "pass|fail|skip|error",
      "violations": [
        {
          "rule": "structural.complexity.cyclomatic",
          "file": "src/router.py",
          "line": 42,
          "symbol": "dispatch",
          "message": "CCX 24 exceeds 10 (complex)",
          "severity": "error",
          "value": 24,
          "threshold": 10
        }
      ],
      "summary": { ... }
    }
  }
}
```

**Decision tree:**
1. Check `summary.result` — if `"pass"`, stop (in passive mode, say nothing)
2. If `"fail"`, iterate `rules` — skip entries with `status: "pass"` or `"skip"`
3. For each failing rule, take the `violations` list sorted by `value` desc
4. Use the `message` field directly — it already contains the threshold comparison
5. Use `file`, `line`, `symbol` to point the user to the location

**Exit codes** (if running via shell):
- `0` = clean
- `1` = violations found
- `2` = config or runtime error

## Reporting to the user

**Passive mode template:**
```
slop: <N> violations in files I touched — <file>:<line> <symbol> (<message>) is the worst. Address these?
```

If clean, say nothing.

**Active mode template:**
```
slop results (<root>):

structural.complexity: <N> violations
  - <file>:<line> <symbol> — <message>
  - <file>:<line> <symbol> — <message>
  - ...and <M> more

structural.hotspots: clean
structural.packages: 2 warnings
  - <pkg> — <message>

structural.deps: clean
structural.class: clean

<total> violations, <rules_checked> rules checked
```

Omit disabled rules. Omit clean categories if the user only asked about
a specific concern.
