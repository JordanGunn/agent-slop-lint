# After: what the refactor actually looked like

The earlier post ([before.md](before.md)) ended on "not refactoring any of
this before publishing." Refactored it a few days later. This post shows
the actual diffs and the metrics before versus after, with no embellishment.

Summary up top:

- One if-chain became a dispatch dict (`cli.main`)
- One 125-line function became three small helpers plus a slim orchestrator (`engine.run_lint`)
- One 85-line function became two helpers plus a thin body (`run_distance`)
- One nested for-loop body got pulled into a helper (`cmd_doctor`)

Four changes. 88 tests stayed green throughout.

## cli.main: 1024 paths to 8

Before:

```python
if args.command == "init":
    return cmd_init(getattr(args, "profile", "default"))
if args.command == "skill":
    return cmd_skill(args.directory)
if args.command == "hook":
    return cmd_hook(disable=getattr(args, "disable", False))
if args.command == "rules":
    return cmd_rules()
if args.command == "schema":
    return cmd_schema()
if args.command == "lint":
    return cmd_lint(args)
if args.command == "check":
    return cmd_check(args)
if args.command == "doctor":
    return cmd_doctor()

parser.print_help()
return 0
```

After:

```python
dispatch = {
    "init":   lambda a: cmd_init(getattr(a, "profile", "default")),
    "skill":  lambda a: cmd_skill(a.directory),
    "hook":   lambda a: cmd_hook(disable=getattr(a, "disable", False)),
    "rules":  lambda _: cmd_rules(),
    "schema": lambda _: cmd_schema(),
    "lint":   cmd_lint,
    "check":  cmd_check,
    "doctor": lambda _: cmd_doctor(),
}

handler = dispatch.get(args.command)
if handler is None:
    parser.print_help()
    return 0
return handler(args)
```

NPath went from 1024 to 8 because NPath multiplies sequential branches
(Nejmeh 1988). Ten sequential ifs gave 2^10 = 1024 paths. After the
refactor there are three binary decisions (the color flag near the top,
the default-to-lint fallback, the handler lookup), which is 2^3 = 8.

The lambdas are slightly unfortunate. They exist because the handlers
take different shapes of argument: `cmd_init` wants `profile`, `cmd_skill`
wants `directory`, `cmd_hook` wants `disable`. Unifying all eight to the
signature `(args) -> int` at the cost of a few lambdas was cleaner than
the ten sequential ifs it replaced. If the handlers ever grow a common
shape the lambdas go away.

## engine.run_lint: three concerns, three helpers

The before version was one 125-line function doing three things that were
only incidentally related: work out which rules to run, run each one,
then roll the results into a final verdict. The three metrics that
flagged it (cyclomatic per McCabe 1976, Halstead Volume and Difficulty
per Halstead 1977, NPath per Nejmeh 1988) all agreed from different
angles. The fix was one per concern.

Rule selection got extracted to `_select_rules`:

```python
def _select_rules(filter_rule, filter_category):
    """Resolve filters to a list of rules to run.

    Raises KeyError(filter) if the filter matches no rule or category.
    """
    if filter_rule:
        rule_def = RULES_BY_NAME.get(filter_rule)
        if rule_def is not None:
            return [rule_def]
        prefix = filter_rule + "."
        prefix_matches = [r for r in RULE_REGISTRY if r.name.startswith(prefix)]
        if prefix_matches:
            return prefix_matches
        raise KeyError(filter_rule)
    if filter_category:
        matches = RULES_BY_CATEGORY.get(filter_category, [])
        if not matches:
            raise KeyError(filter_category)
        return matches
    return list(RULE_REGISTRY)
```

The KeyError convention was a minor judgment call. The alternative was
returning a tuple of `(rules, error_result_or_none)` or a union type.
Raising was less typing ceremony and the catch site (one level up)
produces the same LintResult either way.

Per-rule execution got extracted to `_execute_rule`:

```python
def _execute_rule(rule_def, root, rc, config):
    try:
        result = rule_def.run(root, rc, config)
    except Exception as e:
        return RuleResult(
            rule=rule_def.name, status="error",
            errors=[f"{type(e).__name__}: {e}"],
        )
    if result.errors and result.status == "pass":
        result.status = "error"
    return result
```

The overall-verdict roll-up got extracted to `_overall_status`:

```python
def _overall_status(rule_results, total_violations) -> str:
    if any(r.status == "error" for r in rule_results.values()):
        return "error"
    if total_violations > 0:
        return "fail"
    return "pass"
```

With those three pulled out, what remains of `run_lint` is almost pure
orchestration: call `_select_rules`, loop over each rule calling
`_execute_rule`, count violations, return the LintResult with
`_overall_status` as its verdict.

## run_distance: same shape, same fix

run_distance had the same problem. Language resolution, kernel invocation,
and violation construction all in one function. Extracted
`_resolve_languages` and `_check_package`:

```python
def _resolve_languages(rule_languages, slop_languages):
    candidates = rule_languages or slop_languages or _SUPPORTED_LANGUAGES
    return [lang for lang in candidates if lang in _SUPPORTED_LANGUAGES]


def _check_package(pkg, max_distance, fail_on_zone, severity):
    reasons = []
    if pkg.distance is not None and pkg.distance > max_distance:
        reasons.append(f"D'={pkg.distance:.2f} exceeds {max_distance}")
    if pkg.zone in fail_on_zone:
        reasons.append(f"Zone of {pkg.zone.title()}")
    if not reasons:
        return None
    return Violation(...)
```

`_resolve_languages` is worth a note. The before version was an
if/elif/else ladder. The after version leans on `x or y or z` because
empty lists are falsy in Python, which lets the selection collapse into
one expression. Same semantics. Fewer branches for the metric to count.

## cmd_doctor: one helper, barely

cmd_doctor was one point over the cognitive threshold (Campbell 2018 puts
the default at 15, and cmd_doctor was at 16). Fix was minor: pull the
per-binary formatting out into a helper so the for-loop body collapses to
three lines. Not particularly satisfying. But the metric flagged the
nesting and the refactor costs nothing.

## The numbers

| Function | Metric | Before | After | Default threshold |
|---|---|---|---|---|
| `engine.run_lint` | CCX | 17 | 9 | 10 |
| `engine.run_lint` | CogC | 26 | 13 | 15 |
| `engine.run_lint` | Volume | 1763 | 1034 | 1500 |
| `engine.run_lint` | Difficulty | 30.9 | 18.0 | 30 |
| `engine.run_lint` | NPath | 450 | 14 | 400 |
| `run_distance` | CCX | 14 | 8 | 10 |
| `run_distance` | CogC | 20 | 10 | 15 |
| `cli.main` | CCX | 11 | 4 | 10 |
| `cli.main` | NPath | 1024 | 8 | 400 |
| `cmd_doctor` | CogC | 16 | 6 | 15 |

The biggest number on the page is the `cli.main` NPath collapse, which
reads well but is slightly misleading. The if-chain was already a dispatch
table, just spelled as procedural code. Replacing it with an actual
dispatch table did not so much "reduce complexity" as "stop lying about
what the function was."

## What the metrics actually asked for

None of these refactors were clever. They were the things anyone
reviewing the code with fresh eyes would flag within a minute. The
if-chain wanted to be a dict. The three-concerns-in-one function wanted
to be three functions. `cmd_doctor` wanted its nested loop body pulled
into a helper. The only reason the fixes had not happened already is
that nobody had reviewed the code with fresh eyes since it was written.

Which is the argument for automated quantitative signals over human
review alone. The code had been read dozens of times by me and by various
agents during ordinary development. Nobody had reached for "hey, this
function is doing three things." The metric did, reliably, the first
time it was pointed at the file.

## .slop.toml cleanup

Before the refactor, the dogfood config overrode six thresholds with
explanatory comments like `# engine.run_lint V=1763 — refactor target`.
The config was 44 lines. After the refactor, those overrides are gone.
The config is down to 12 lines using default thresholds, and the only
rules still disabled are `hotspots` (the project is three weeks old, no
meaningful churn history) and `packages` (the small four-package corpus
makes I/A/D' numbers too noisy to trust).

The relaxed thresholds were load-bearing stale documentation. The
refactor removed the need for them.

## Sources

- McCabe, T. J. (1976). A Complexity Measure.
- Halstead, M. H. (1977). Elements of Software Science.
- Nejmeh, B. A. (1988). NPATH: A Measure of Execution Path Complexity.
- Campbell, G. A. (2018). Cognitive Complexity: A new way of measuring
  understandability.
- Martin, R. C. (2002). Agile Software Development: Principles, Patterns,
  and Practices.
