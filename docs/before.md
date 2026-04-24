# What happens when the linter is pointed at itself

> Pre-refactor snapshot. File paths and line numbers in this post refer to
> the codebase as it was before the refactor documented in
> [after.md](after.md). The code that was flagged here has since been
> restructured; the "after" post shows what that looked like.

Shipped a code-quality linter to PyPI a couple of weeks ago. Been running it
against real code for a few days. Then, on a whim, ran it against its own
source with the default thresholds instead of the relaxed ones the repo
normally uses.

10 violations, 1 advisory, exit code 1.

```
complexity
  cyclomatic
    ✗ cli/slop/engine.py:16 run_lint — CCX 17 exceeds 10 (moderate)
    ✗ cli/slop/rules/architecture.py:27 run_distance — CCX 14 exceeds 10 (moderate)
    ✗ cli/slop/cli.py:122 main — CCX 11 exceeds 10 (moderate)

  cognitive
    ✗ cli/slop/engine.py:16 run_lint — CogC 26 exceeds 15
    ✗ cli/slop/rules/architecture.py:27 run_distance — CogC 20 exceeds 15
    ✗ cli/slop/cli.py:357 cmd_doctor — CogC 16 exceeds 15

halstead
  volume
    ✗ cli/slop/engine.py:16 run_lint — Volume 1763 exceeds 1500
  difficulty
    ✗ cli/slop/engine.py:16 run_lint — Difficulty 30.9 exceeds 30

npath
  ✗ cli/slop/cli.py:122 main — NPath 1024 exceeds 400
  ✗ cli/slop/engine.py:16 run_lint — NPath 450 exceeds 400

packages (python)
  ⚠ cli/slop — D'=1.00 exceeds 0.7; Zone of Pain (I=0.00, A=0.00)
```

The count is not the interesting part. The interesting part is which
functions got flagged, and the fact that three mathematically independent
metrics landed on the same one.

## run_lint, flagged three different ways

The engine's main loop gets hit by cyclomatic, Halstead, and NPath at the
same time.

- Cyclomatic complexity 17 (McCabe 1976). You would need 17 test cases to
  exercise every linearly independent path.
- Halstead Volume 1763, Difficulty 30.9 (Halstead 1977). A measure of the
  function's symbolic density, computed from its distinct operators and
  operands.
- NPath 450 (Nejmeh 1988). NPath multiplies branches instead of adding
  them, so a function with eight sequential ifs has NPath 256, not 8.

Here is the function, abridged:

```python
def run_lint(config, *, filter_category=None, filter_rule=None, display_root=""):
    ...
    if filter_rule:
        rule_def = RULES_BY_NAME.get(filter_rule)
        if rule_def is not None:
            rules_to_run = [rule_def]
        else:
            prefix = filter_rule + "."
            prefix_matches = [r for r in RULE_REGISTRY if r.name.startswith(prefix)]
            if prefix_matches:
                rules_to_run = prefix_matches
            else:
                return LintResult(..., result="error", ...)
    elif filter_category:
        rules_to_run = RULES_BY_CATEGORY.get(filter_category, [])
        if not rules_to_run:
            return LintResult(..., result="error", ...)
    else:
        rules_to_run = list(RULE_REGISTRY)

    for rule_def in rules_to_run:
        rc = config.rule_config(rule_def.category)
        if not rc.enabled or rc.severity == "off":
            ...
            continue
        try:
            result = rule_def.run(root, rc, config)
        except Exception as e:
            result = RuleResult(..., errors=[f"{type(e).__name__}: {e}"])
        if result.errors and result.status == "pass":
            result.status = "error"
        ...
```

The function does rule selection, then per-rule execution, then
aggregation at the end. Each piece is fine on its own. Jamming them into
one function is where the smell comes from, and three different metrics
picked it up from three different angles.

Cyclomatic alone would have flagged this (McCabe's 1976 paper recommended
10 as the upper bound for a "manageable" function). But the same function
showing up under three mathematically independent measures is harder to
hand-wave away, which is the actual argument for multi-metric linting.

## cli.main, NPath 1024

The CLI entry point has this shape:

```python
if args.command == "init":
    return cmd_init(...)
if args.command == "skill":
    return cmd_skill(...)
if args.command == "hook":
    return cmd_hook(...)
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
```

Ten sequential if-blocks counting the two near the top. NPath multiplies
branches, so ten yes/no decisions in a row works out to 2^10 = 1024. The
threshold is 400.

In practice only one branch ever fires per invocation, and NPath does not
know that. What the metric is really saying is that the function's shape
is a dispatch table pretending to be procedural code, and any reader has
to visually confirm "exactly one of these branches runs" before trusting
it. A dict mapping command name to handler collapses the function's NPath
to something like 4.

This was not news. There is a comment next to the relaxed threshold in
the dogfood config saying cli.main is a known refactor target. Seeing the
metric agree with the comment, at exactly the ratio 1024 to 400, was the
kind of thing worth pointing at.

## run_distance, flagged twice

The function that runs Robert Martin's Distance from the Main Sequence is
itself mildly complex (cyclomatic 14, cognitive 20):

```python
def run_distance(root, rule_config, slop_config) -> RuleResult:
    ...
    if rule_languages:
        languages = [lang for lang in rule_languages if lang in _SUPPORTED_LANGUAGES]
    elif slop_config.languages:
        languages = [lang for lang in slop_config.languages if lang in _SUPPORTED_LANGUAGES]
    else:
        languages = list(_SUPPORTED_LANGUAGES)

    for lang in languages:
        result = robert_kernel(...)
        for pkg in result.packages:
            triggered = False
            reasons = []
            if pkg.distance is not None and pkg.distance > max_distance:
                triggered = True
                reasons.append(...)
            if pkg.zone in fail_on_zone:
                triggered = True
                reasons.append(...)
            if triggered:
                violations.append(Violation(...))
```

Same pattern as run_lint. Language resolution, kernel invocation, and
violation construction all in one place. The language-resolution block
could be a helper. The violation construction could be a helper. Nobody
pulled them out because the function works. The metric saw the shape
anyway, and I had not noticed.

## cmd_doctor, cognitive 16

cmd_doctor reports which system binaries are installed. For-loop with a
conditional whose true branch has its own nested string construction.
Cognitive 16, one point over the threshold. Not catastrophic. Listing it
for completeness, not because the refactor is obvious.

## Zone of Pain, with caveat

Robert Martin's package metrics (from Agile Software Development, 2002)
put the top-level slop package at D' = 1.00, the worst possible score.
Instability 0, abstractness 0. The Zone of Pain.

This one needs a caveat. With the vendored kernels excluded (they live
under an _aux directory the dogfood config tells slop to skip), the
codebase has four Python packages, which is a small enough corpus that
the I/A/D' numbers are noisy. In a real multi-package project the metric
carries more information. Including it here not because it is
actionable, but because the raw report includes it and readers should
see the parts that are less trustworthy too.

## What is not happening next

Not refactoring any of this before publishing. The whole point was the
raw, un-gamed output. A follow-up post can show the before and after
once the refactor is real.

## The linter

It is called slop (`agent-slop-lint` on PyPI, source at
https://github.com/JordanGunn/agent-slop-lint). It is a thin wrapper
around a handful of metric kernels that each implement a paper from
1976 through 2002. None of the math is new. What is new is that agents
now write more code per unit of human review than the original authors
of these metrics could have imagined, and the shared mathematical
definitions of "bad code" that those papers gave us are newly
load-bearing.

## Primary sources

- McCabe, T. J. (1976). A Complexity Measure.
- Halstead, M. H. (1977). Elements of Software Science.
- Nejmeh, B. A. (1988). NPATH: A Measure of Execution Path Complexity.
- Chidamber, S. R. and Kemerer, C. F. (1994). A Metrics Suite for
  Object-Oriented Design.
- Martin, R. C. (2002). Agile Software Development: Principles, Patterns,
  and Practices.
- Tornhill, A. (2015). Your Code as a Crime Scene.
