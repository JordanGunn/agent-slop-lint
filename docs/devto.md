---
title: "Agentic Smells: From Qualitative to Quantitative"
published: false
tags: ai, programming, codequality, refactoring
---

Every developer has had the same experience at least once. You pull down code someone else wrote, increasingly often an agent wrote, and something is off. Tests pass. The function returns the right type. The PR description is coherent. But the code is shaped in a way you would not have shaped it, and you cannot quite say what is wrong.

The feeling has a name. The discipline calls it a code smell, a term coined by Kent Beck for his chapter in Fowler's *Refactoring* (1999). A smell, as Beck described it, is a characteristic of source code that hints at a deeper problem, a signal the way a smell from food left in the fridge too long is a signal. The olfactory metaphor is honest. It is, by its own choice of word, an admission that the thing being named resists precise description. Feature Envy, Shotgun Surgery, God Class, Divergent Change. Evocative enough to recognise in a textbook, vague enough to argue about in a code review.

That vagueness was tolerable when every reader of the code had roughly the same nose. Review was the moment where experience enforced invariants nobody had written down, and juniors were expected to catch up by serving their own time.

Now the primary reader of the code is an agent. Agents have no nose. Developers who entered the industry writing on top of LLMs often do not have one either, not because they are bad, but because the path that used to build one (reading, extending, and refactoring code written by more experienced colleagues) compressed into "ask the model." When something feels off, the instinct is to prompt with "this is messy, fix it" or "this function is doing too many things." Natural languages are entropy-rich; "messy" carries as many interpretations as the language has had years to accumulate. The agent does what it can with the ambiguity, and what comes back is messy replaced with messy in a different way. More hidden and subtler, often moved down into a layer of the stack you accepted because it looked too complicated to handle yourself.

As the models get more capable this gets harder to catch, not easier. The output looks correct. The bar for examining it drops. The problem does not surface until a compound failure no one has the context to unwind.

The fix is not a new language for defining what "messy" means in the absolute. The fix is a signal strong enough, and well-documented enough in the model's training data, to collapse the interpretation space. "Cognitive Complexity 26 on this function, threshold is 15" is not a feeling. It is an arithmetic statement whose definition, computation, and remediation patterns all sit in the same canonical corpus the model learned to write code from. Ask the model to fix a smell and you often get a different smell. Ask the model to bring Cognitive Complexity below 15 and you get the specific shape of refactor that Campbell (2018) says reduces that metric, not a guess about what you meant.

## The research was already there

A body of software-engineering research from 1976 through 2018 had already reduced most of "feels wrong" to arithmetic:

- Thomas McCabe gave us **cyclomatic complexity** in 1976, defining the number of linearly independent paths through a function and recommending 10 as the upper bound for "manageable."
- Maurice Halstead followed in 1977 with operator-and-operand counts that produce **Volume** (the information content of a function) and **Difficulty** (a reader's cognitive burden).
- Brian Nejmeh added **NPath** in 1988, which multiplies sequential branches instead of adding them. This catches combinatorial path explosion that cyclomatic complexity underreports.
- Chidamber and Kemerer published the **CK metric suite** in 1994, including CBO for class coupling, DIT for inheritance depth, and WMC for weighted methods per class.
- Robert C. Martin formalised the **Distance from the Main Sequence** (D') the same year, pulling package-level architectural rot into a single scalar.
- John Lakos articulated the **Acyclic Dependencies Principle** in 1996, later expanded in Martin's *Agile Software Development* in 2002.
- Adam Tornhill's churn-weighted **hotspot** analysis arrived in 2015.
- G. Ann Campbell introduced **Cognitive Complexity** in 2018, penalising nesting in a way cyclomatic never did.

Most working developers memorised a few of these for an exam and promptly forgot them. Not out of laziness. They forgot them because intuition, once developed, was cheaper to apply than the math. You do not need to compute a class's CBO if you can look at the `import` block and feel in your gut that there are too many things. The metrics sat quietly in conference proceedings and textbooks, precise and computable and largely unread, because the humans who needed them had developed a workaround.

The workaround does not survive the shift to agent-authored code. Agents have no gut feel. They have tokens. "This function feels like it is doing too much" is a statement a model will agree with in any direction you push it. "This function has Cognitive Complexity 26, Cyclomatic 17, and NPath 450" is not. One is conversation. The other is arithmetic. Agents negotiate conversation. They cannot negotiate arithmetic.

## A worked example

Last week I pointed a metric suite at its own source code, running with out-of-the-box thresholds. Result: ten violations, one advisory, exit code 1.

```
complexity
  cyclomatic
    cli/slop/engine.py:16 run_lint — CCX 17 exceeds 10
    cli/slop/rules/architecture.py:27 run_distance — CCX 14 exceeds 10
    cli/slop/cli.py:122 main — CCX 11 exceeds 10

  cognitive
    cli/slop/engine.py:16 run_lint — CogC 26 exceeds 15
    cli/slop/rules/architecture.py:27 run_distance — CogC 20 exceeds 15
    cli/slop/cli.py:357 cmd_doctor — CogC 16 exceeds 15

halstead
    cli/slop/engine.py:16 run_lint — Volume 1763 exceeds 1500
    cli/slop/engine.py:16 run_lint — Difficulty 30.9 exceeds 30

npath
    cli/slop/cli.py:122 main — NPath 1024 exceeds 400
    cli/slop/engine.py:16 run_lint — NPath 450 exceeds 400
```

The interesting thing about this report is which functions got flagged and how the metrics agreed. `run_lint` appears five times: once for cyclomatic, once for cognitive, twice for Halstead, once for NPath. Three mathematically independent metrics measuring three different things (path count, symbolic density, acyclic path count) all pointing at the same 125-line function from three different angles.

Here is that function, edited for brevity:

```python
def run_lint(config, *, filter_category=None, filter_rule=None, ...):
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
            rule_results[rule_def.name] = RuleResult(...)
            continue
        try:
            result = rule_def.run(root, rc, config)
        except Exception as e:
            result = RuleResult(..., errors=[...])
        if result.errors and result.status == "pass":
            result.status = "error"
        ...
```

The function is doing three things that are only incidentally related: resolving which rules to run, running each rule with error handling, and rolling everything up into a final verdict. Each piece is defensible in isolation. Jamming them into one function is where the three metrics picked up the smell.

The refactor pulled each concern into its own helper. `_select_rules` took the rule-resolution logic. `_execute_rule` took the per-rule try-except with error coercion. `_overall_status` took the verdict roll-up. After the change, `run_lint` itself is about forty lines and does pure orchestration.

The second flagged function is worth showing because the NPath number is vivid. The CLI entry point before the refactor:

```python
def main(argv=None):
    parser = create_parser()
    args = parser.parse_args(argv)
    if getattr(args, "no_color", False):
        set_color(False)
    if args.command is None:
        args.command = "lint"
        ...
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
    parser.print_help()
    return 0
```

Ten sequential if-blocks. NPath multiplies sequential branches, so ten binary decisions in a row produce 2^10 = 1024 execution paths. The threshold is 400. The refactor turned it into a dispatch dict:

```python
def main(argv=None):
    parser = create_parser()
    args = parser.parse_args(argv)
    if getattr(args, "no_color", False):
        set_color(False)
    if args.command is None:
        args.command = "lint"
        ...

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

NPath dropped to 8. The if-chain was already a dispatch table pretending to be procedural code. Replacing it with an actual dispatch table did not so much reduce complexity as stop lying about what the function was.

Full delta across the four flagged functions:

| Function | Metric | Before | After | Default threshold |
|---|---|---|---|---|
| `run_lint` | CCX | 17 | 9 | 10 |
| `run_lint` | CogC | 26 | 13 | 15 |
| `run_lint` | Volume | 1763 | 1034 | 1500 |
| `run_lint` | Difficulty | 30.9 | 18.0 | 30 |
| `run_lint` | NPath | 450 | 14 | 400 |
| `run_distance` | CCX | 14 | 8 | 10 |
| `run_distance` | CogC | 20 | 10 | 15 |
| `main` | CCX | 11 | 4 | 10 |
| `main` | NPath | 1024 | 8 | 400 |
| `cmd_doctor` | CogC | 16 | 6 | 15 |

Ten violations before, zero after. All 88 tests stayed green across the refactors.

## Why not just run SonarQube

Reasonable objection. These metrics have lived inside SonarQube, ESLint complexity plugins, `gocyclo`, and `radon` for over a decade. The measurement is not the novelty. What is new is that none of those tools fit inside an agent loop.

Traditional linters assume a human running them on a workstation or in CI. Startup time runs into seconds. Configuration files proliferate. Analysis is language-specific, with a separate engine per language to install, version, and maintain. The output is shaped for humans reading reports, not for agents parsing tokens. An agent that has to spawn a JVM, load rulesets from a YAML file, and parse an XML report between turns is an agent whose chat-interface UX collapses under its own tooling.

The current generation of agentic tooling runs on a different stack. `fd` for file discovery. `ripgrep` for text search. `tree-sitter` for language-agnostic parsing out of a single binary, across dozens of languages, with no per-language runtime to maintain. These tools are fast, they produce token-friendly output, they have no configuration ceremony, and they do not stall the snappy back-and-forth that makes a chat interface usable. slop is built on this stack. That is the architectural bet: metrics whose computation feels like every other tool call the agent makes, not a separate ceremony the agent has to schedule around.

## Why this matters more now, not less

None of the fixes above were clever. They were the things any experienced reviewer would flag in a minute. The if-chain wanted to be a dict. The three-concerns-in-one function wanted to be three functions. The nested formatting inside a for-loop wanted to be a helper. The reason those fixes had not happened already is that the code had been written, reviewed, and extended by agents, and no human had read any of it closely. Under ordinary development the code gets read dozens of times; under agentic development the code gets read primarily by the thing that wrote it, which is precisely the reader least likely to notice its smells.

The common response is "but surely a human reviews this before merge." Sometimes. And here is the uncomfortable part: a human reviewer on their fourth PR of the afternoon, working against a deadline, presented with a 400-line diff authored by an agent, is more likely to wave through incoherent code, not less. The harder it is to understand, the higher the probability of approval, because the cognitive cost of asking for changes exceeds the cognitive cost of trusting the agent. Confusion plus a deadline equals approval. The reviewer's gut may say "something is wrong here," but without a name for it, the gut loses to the deadline every time.

This is where the forty-year-old metrics earn their keep. "This function has Cognitive Complexity 26, threshold is 15" is not something a reviewer can wave through under time pressure without admitting they are doing it. It is specific, it has a threshold, it has a citation, and the agent can be instructed to fix it with the same precision. The metric is the vocabulary that lets the concern land faster than the deadline can dissolve it.

The metrics are also what an agent can be held to. Not by self-reporting, which is subject to the same agreement-optimisation that makes natural-language self-assessment worthless, but by running them as external tools whose output the agent cannot massage. A linter that computes CCX from the AST and reports 17 is a fixed referent. The agent cannot talk the number down. The agent can only change the code until the number drops.

## The tool

The linter I used is called slop. It is open source under Apache 2.0, on PyPI as `agent-slop-lint`, source at [github.com/JordanGunn/agent-slop-lint](https://github.com/JordanGunn/agent-slop-lint). It ships rules wrapping the metric kernels discussed above, computed via tree-sitter ASTs across Python, TypeScript, JavaScript, Go, Rust, Java, and C#. Running `slop lint` executes them all with sane defaults and exits non-zero on violations, which makes it easy to wire into CI or a pre-commit hook, and easy to put into an agent's toolchain so the metric is something the agent can inspect between turns rather than something that surprises it at merge time.

The rules and their primary sources:

| Rule family | What it measures | Source |
|---|---|---|
| complexity | per-function path count, reading difficulty, per-class aggregate | McCabe 1976, Campbell 2018, Chidamber & Kemerer 1994 |
| halstead | per-function information content and operator/operand density | Halstead 1977 |
| npath | per-function multiplicative path count | Nejmeh 1988 |
| hotspots | complexity-weighted churn over time | Tornhill 2015 |
| packages | Distance from the Main Sequence at package scope | Martin 1994, 2002 |
| deps | import cycles (Acyclic Dependencies Principle) | Lakos 1996, Martin 2002 |
| class | coupling, inheritance depth and breadth | Chidamber & Kemerer 1994 |

None of the math is new. What is new is that agents now write far more code per unit of human review than the original authors of these metrics could have imagined, and the shared-vocabulary instruments they gave us are load-bearing in a way they were never load-bearing before.

The metrics are forty years old. They are precise, computable, and largely unread. That is fixable.
