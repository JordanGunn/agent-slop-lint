# Configuration Reference

This guide explains every configurable value in slop, what it means in practice, and when to change it. The goal is to help you tune slop to your project rather than disable it when a rule gets in the way.

slop reads config from `.slop.toml` (or `[tool.slop]` in `pyproject.toml`). Generate a starter config with `slop init`.

## A note on default thresholds

slop cites well-established metrics (McCabe, Chidamber & Kemerer, Halstead, Nejmeh, Martin, Tornhill) and most defaults match the numbers from those original sources. Three do not, and this section documents why so readers who open the cited papers can reconcile the discrepancy.

| Rule | Citation's threshold | slop default | Why slop diverges |
|---|---:|---:|---|
| `complexity.weighted` (WMC) | ~50 (1990s industry convention) | 40 | Contemporary OO advice (Fowler, Martin) treats classes with more than a handful of responsibilities as refactor candidates. 40 aligns with modern practice and catches god-class drift earlier. |
| `halstead.volume` | ~1000 (SonarSource-style) | 1500 | The 1000 ceiling flags legitimate orchestration code (formatters, dispatchers, fused pipelines) that are not actually rot. 1500 still flags the pathological case where three responsibilities fused into one function, without penalising honest breadth-heavy code. |
| `npath` | 200 (Nejmeh 1988) | 400 | Nejmeh's 200 was calibrated on pre-OO C code at AT&T Bell Labs in 1988. Modern CLI dispatch patterns (click, argparse, cobra) routinely produce honest `main` functions at NPath 256-512 because each `if args.command == "X"` doubles the count. 400 raises the floor above typical dispatch while still flagging the 10-sequential-if combinatorial explosion (NPath=1024). |

Every other rule's default matches the cited source.

## Rule reference

### complexity.cyclomatic

**What it measures:** McCabe's Cyclomatic Complexity (1976) — the number of linearly independent paths through a function. Each `if`, `for`, `while`, `case`, `catch`, and boolean operator (`&&`, `||`) adds a path.

**Default threshold:** `CCX > 10`

**What the numbers mean:**
- **1–10** — straightforward. Easy to test, easy to read.
- **11–20** — moderate. More paths means more test cases needed for coverage.
- **21–50** — complex. Refactor candidate. Hard to hold in your head.
- **51+** — untestable. Exhaustive path coverage is impractical.

**When to raise it:** Legacy codebases with many functions in the 11–15 range that are stable and well-tested. Raising to 15 silences noise without hiding real problems.

**When to lower it:** Greenfield projects or strict teams. A threshold of 6–8 forces smaller functions from the start.

```toml
[rules.complexity]
cyclomatic_threshold = 10
```

### complexity.cognitive

**What it measures:** Campbell's Cognitive Complexity (2018) — a proxy for how hard a function is to *read*, not just how many paths it has. Nesting adds exponential penalty; boolean operator sequences are collapsed (three `&&` in a row count as one increment, not three).

**Default threshold:** `CogC > 15`

**What the numbers mean:** CogC tracks reading difficulty more closely than CCX. A deeply nested function with CCX=8 might have CogC=20 because the nesting penalty compounds. Conversely, a flat function with many sequential branches might have CCX=15 but CogC=10.

**When to raise it:** Codebases with complex but well-structured branching (e.g., parsers, state machines). Raising to 20–25 lets structured complexity through while still catching spaghetti.

**When to lower it:** Teams where readability is the primary concern. 10 is aggressive but effective.

```toml
[rules.complexity]
cognitive_threshold = 15
```

### complexity.weighted

**What it measures:** Weighted Methods per Class (Chidamber & Kemerer 1994) — the sum of CCX across all methods in a class. High WMC means the class is doing too much.

**Default threshold:** `WMC > 40`

**What the numbers mean:** A class with 10 methods averaging CCX=4 each has WMC=40. That is the boundary where a class is doing enough that a reader has to actively hold its pieces in their head. A class with WMC=150 is almost certainly a god class.

**Why the default is 40 and not 50.** The older industry convention of WMC > 50 was tuned for 1990s OO codebases where classes of 20-plus methods were routine. Contemporary OO advice (Fowler, Martin) treats classes with more than a handful of responsibilities as refactor candidates. 40 is closer to current practice and catches god-class drift earlier. If you maintain a codebase with legitimately large classes (framework base classes, protocol handlers), raising to 50 or 60 is reasonable.

**When to raise it:** Large classes that are well-factored internally (clear method boundaries, low coupling between methods). Raising to 75–100 focuses on the truly egregious cases.

**When to lower it:** Projects enforcing single-responsibility strictly. WMC=30 catches classes that are starting to accumulate responsibilities.

**When to disable:** Projects with no classes (pure functional style, Go without receiver types, scripting). WMC is meaningless if there are no classes.

```toml
[rules.complexity]
weighted_threshold = 50
```

### halstead.volume

**What it measures:** Halstead's (1977) Volume metric — `V = Length × log2(Vocabulary)`, where Length is total operator/operand occurrences and Vocabulary is the distinct-operator + distinct-operand count. Volume proxies the information content of a function. Large Volume means "a lot of stuff is happening in here."

**Default threshold:** `V > 1500`

**What the numbers mean:** Volume scales with both size and diversity. A 20-line function with five variables and standard arithmetic lands around V=150. A 60-line function touching twenty symbols and many operators can hit V=1200 without looking obviously complex to CCX or CogC. That is the niche Halstead covers.

**Why the default is 1500 and not 1000.** SonarSource-style V > 1000 is a reasonable boundary for functions that were *meant* to be decomposed. In practice, legitimate orchestration code (format_human, run_lint, dispatch functions, serializers that touch many fields) often sits in the 1200-1800 range without being rot. 1500 still flags the pathological case where three responsibilities fused into one function (typical V of 2000-plus) while leaving honest orchestration alone.

**When to raise it:** Long formatters, serializers, or state-machine dispatchers that legitimately reference many symbols. Raising to 2000 leaves room for breadth-heavy code.

**When to lower it:** Greenfield projects wanting tight function sizes. Lowering to 1000 or 800 forces decomposition early.

**When Halstead differs from CCX:** CCX counts control-flow paths. Halstead counts tokens. A function with low CCX but 40 unique operands (e.g. a big dict construction) will have high Volume but low CCX. Halstead catches that; CCX misses it.

```toml
[rules.halstead]
volume_threshold = 1000
```

### halstead.difficulty

**What it measures:** Halstead's (1977) Difficulty — `D = (n1/2) × (N2/n2)` where n1 is unique operators, n2 is unique operands, and N2 is total operand occurrences. Difficulty proxies the cognitive burden of reading one line: how many operators the reader has to track and how often operands repeat.

**Default threshold:** `D > 30`

**What the numbers mean:** A simple arithmetic function lands around D=5–10. Functions approaching D=30 use most of their language's operator surface and reuse a lot of operands — typical of parsers, expression evaluators, or densely-fused pipelines. D=50+ is almost always a sign that a function is doing the work of three.

**When to raise it:** Numerical or DSL interpreter code where operator density is intrinsic to the domain. Raising to 50 leaves room for legitimate density.

**When to lower it:** Teams that want to catch cognitive density early. D=20 is aggressive but effective.

```toml
[rules.halstead]
difficulty_threshold = 30
```

### npath

**What it measures:** Nejmeh's (1988) NPath complexity — the count of acyclic execution paths through a function. Unlike McCabe's CCX which is additive (each branch adds 1 to the count), NPath is multiplicative: sequential branches multiply path counts. Ten sequential independent `if` statements produce CCX=11 but NPath=1024. NPath catches combinatorial explosion that CCX massively underreports.

**Default threshold:** `NPath > 400`

**What the numbers mean:** A linear function has NPath=1. A single `if` doubles it to 2. A function with five sequential ifs has NPath=32; ten sequential ifs produces NPath=1024. The canonical Nejmeh (1988) threshold was 200, chosen because it corresponds to roughly the combinatorial limit of what fits in a reviewer's head.

**Why the default is 400 and not 200.** Nejmeh's 200 came from 1988 AT&T Bell Labs research on small pre-OO C functions before modern CLI dispatch patterns existed. Contemporary code routinely includes `main` functions with eight to ten subcommand branches (click, argparse, cobra), and each branch doubles NPath. Honest dispatch functions sit at NPath 256-512 and are not rot. 400 raises the floor above the typical CLI dispatch pattern while still flagging genuine combinatorial explosion (NPath > 500 and especially > 1000 almost always indicates branches that should have been decomposed into handler functions).

**When NPath differs from CCX:** CCX treats `if a: f(); if b: g(); if c: h()` as three independent decisions (CCX=4). NPath treats them as combinatorial because each branch independently affects whether the next one executes in a particular state (NPath=8). For code where the branches are genuinely independent, NPath is the more honest metric.

**When to raise it:** Parsers, validators, or code handling genuinely independent flags where combinatorial reasoning is intrinsic. Raising to 800 or 1000 accommodates legitimate branch fan-out.

**When to lower it:** Greenfield projects. NPath=200 returns to Nejmeh's canonical ceiling.

```toml
[rules.npath]
npath_threshold = 200
```

### hotspots

**What it measures:** Growth-weighted complexity per file — Tornhill's (2015) hotspot framework with LOC delta as the churn proxy. Score = `sum_ccx × max(0, net_loc_delta)`. Files that are complex AND growing fast are where architectural damage accumulates.

**Default:** `14 days ago` window, `min_commits = 2`, fail on `hotspot` quadrant

**Key settings:**

| Setting | Default | Description |
|---|---|---|
| `since` | `"14 days ago"` | How far back to look. The 14-day default is tuned for agentic work — agents accumulate rot in days, not months. |
| `min_commits` | `2` | Files touched only once in the window are filtered out as noise. |
| `fail_on_quadrant` | `["hotspot"]` | Which quadrants trigger a violation. |

**Quadrants explained:**
- **hotspot** — complex AND growing fast. The worst case. Always worth investigating.
- **stable_complex** — complex but not growing. Legacy code. Not urgent.
- **churning_simple** — growing fast but not complex. Watch it — complexity follows growth.
- **calm** — low on both axes. No action needed.

**When to widen the window:** Human-pace repos where 14 days captures too little. Set `since = "90 days ago"` or `since = "6 months ago"`.

**When to add quadrants to fail_on:** Teams that want to catch `churning_simple` files before they become hotspots: `fail_on_quadrant = ["hotspot", "churning_simple"]`.

**When to disable:** Repos with no git history, or when running on a shallow clone where history is unavailable.

```toml
[rules.hotspots]
since = "14 days ago"
min_commits = 2
fail_on_quadrant = ["hotspot"]
```

### packages

**What it measures:** Robert C. Martin's (1994) Distance from the Main Sequence — how far a package's balance of abstractness (A) and instability (I) deviates from the ideal. D' = |A + I - 1|. A package in the "Zone of Pain" (D' > threshold, low A, low I) is concrete and depended on by many — hard to change.

**Default threshold:** `D' > 0.7`, fail on `pain` zone

**What the numbers mean:**
- **D' near 0** — on the Main Sequence. Balanced.
- **D' near 1** — in a zone. Either Pain (concrete + stable = rigid) or Uselessness (abstract + unstable = over-engineered).

**Currently supports:** Every language slop covers: Go, Python, Java, C#, TypeScript, JavaScript, Rust, Julia. Abstract-type detection is language-specific: Go interfaces, Python ABCs / Protocols, Java and C# `interface` plus `abstract class`, TypeScript `interface` plus `abstract class`, Rust `trait`, Julia `abstract type`. JavaScript has no `interface` or `abstract class` in the language itself, so every `class` is counted as concrete (Ja=0); this is accurate but means JS packages with `Ca > 0` will reliably land in Zone of Pain. Files in an unsupported language are silently skipped.

**When to raise it:** Mature codebases where some packages are legitimately concrete and stable (e.g., utility packages). Raising to 0.85 focuses on extreme cases.

**When to lower it:** Projects with strict layered architecture. 0.5 catches packages drifting from the ideal early.

**When to disable:** Single-package projects where the metric is ill-defined. JavaScript-only projects where you don't want the expected noise from the "no abstract concept" limitation; the rule is `severity = "warning"` by default, so it reports without failing the build.

```toml
[rules.packages]
max_distance = 0.7
fail_on_zone = ["pain"]
severity = "warning"
```

### deps

**What it measures:** Dependency cycles between modules. The Acyclic Dependencies Principle (Lakos 1996; Martin 2002) holds that cycles prevent independent reasoning, testing, and extraction of any module in the cycle — every change touches the whole loop. slop detects them with Tarjan's (1972) SCC algorithm on the import graph.

**Default:** Fail on any cycle.

**When to disable:** Very early-stage prototypes where module boundaries are still forming. Re-enable as soon as the structure stabilizes — cycles that form early tend to calcify.

```toml
[rules.deps]
fail_on_cycles = true
```

### orphans

**What it measures:** Unreferenced symbols (functions, classes, constants) — dead code candidates. Uses tree-sitter for definition detection and ripgrep for reference counting.

**Default:** Disabled. This is advisory, not a gate.

**Why it's off by default:** False positives are common. Symbols may be referenced by:
- Dynamic dispatch (`getattr`, reflection)
- String-based lookups (ORMs, serializers)
- External consumers (public API, CLI entry points)
- Test fixtures

**When to enable:** Periodic cleanup audits. Enable, review the output, delete what's clearly dead, then disable again. Don't leave it on as a CI gate — the false positive rate will erode trust.

**Confidence levels:**
- `"high"` — only flag symbols with zero textual references anywhere in the codebase. Safest.
- `"medium"` — include symbols with very few references (may be test-only). More aggressive.

```toml
[rules.orphans]
enabled = true            # for cleanup audits
min_confidence = "high"
severity = "warning"
```

### class.coupling

**What it measures:** Coupling Between Object Classes (Chidamber & Kemerer 1994) — the count of distinct external classes referenced by a class. High CBO means a class depends on many others and is fragile to change.

**Default threshold:** `CBO > 8`

**What the numbers mean:** A class with CBO=3 is focused. CBO=8 means it references 8 other classes — changes to any of them could break it. CBO=15+ is a strong signal of a class that's trying to do everything.

**When to raise it:** Facade or coordinator classes that legitimately reference many collaborators. Raising to 12–15 focuses on truly tangled classes.

**When to lower it:** Microservice or clean-architecture projects. CBO=5 enforces tight boundaries.

```toml
[rules.class]
coupling_threshold = 8
```

### class.inheritance.depth

**What it measures:** Depth of Inheritance Tree (Chidamber & Kemerer 1994) — levels of parent classes above a given class. Deep hierarchies make behaviour hard to predict because methods can be overridden at any level.

**Default threshold:** `DIT > 4`

**What the numbers mean:** DIT=1 means one parent (common). DIT=4 means four levels deep — changes to any ancestor can subtly change this class's behaviour. DIT=7+ is a code smell in virtually any project.

**When to raise it:** Framework-heavy codebases (e.g., Django models inherit from multiple framework bases). Raising to 6 accommodates framework depth without masking project-level inheritance problems.

**When to lower it:** Projects that favor composition over inheritance. DIT=2 catches any inheritance beyond the immediate base class.

```toml
[rules.class]
inheritance_depth_threshold = 4
```

### class.inheritance.children

**What it measures:** Number of Children (Chidamber & Kemerer 1994) — direct subclass count. A class with many children is a high-leverage change point — modifying its interface ripples to every child.

**Default threshold:** `NOC > 10`

**What the numbers mean:** NOC=3 is healthy polymorphism. NOC=10 means 10 subclasses depend on this parent's contract — any change to the parent is a blast radius of 10. NOC=20+ suggests the parent is being used as a dumping ground.

**When to raise it:** Plugin architectures or type hierarchies where many implementations of a base are expected by design. Raising to 15–20 is appropriate.

**When to lower it:** Projects that want to catch growing hierarchies early. NOC=5 flags parents before the subclass count gets out of hand.

```toml
[rules.class]
inheritance_children_threshold = 10
```

## Profiles

Generate a profile directly with `slop init`:

```bash
slop init              # default — balanced for most projects
slop init lax          # lax — legacy codebases or gradual adoption
slop init strict       # strict — greenfield or quality-focused teams
```

Or copy one of the configs below into your `.slop.toml` manually.

### Default — balanced for most projects

```toml
[rules.complexity]
cyclomatic_threshold = 10
cognitive_threshold = 15
weighted_threshold = 40

[rules.halstead]
volume_threshold = 1500
difficulty_threshold = 30

[rules.npath]
npath_threshold = 400

[rules.hotspots]
since = "14 days ago"
min_commits = 2
fail_on_quadrant = ["hotspot"]

[rules.packages]
max_distance = 0.7
severity = "warning"

[rules.deps]
fail_on_cycles = true

[rules.orphans]
enabled = false

[rules.class]
coupling_threshold = 8
inheritance_depth_threshold = 4
inheritance_children_threshold = 10
```

### Lax — for legacy codebases or gradual adoption

Start here if the default profile produces too many violations to act on. Tighten over time.

```toml
[rules.complexity]
cyclomatic_threshold = 20
cognitive_threshold = 25
weighted_threshold = 80

[rules.halstead]
volume_threshold = 3000
difficulty_threshold = 50

[rules.npath]
npath_threshold = 1000

[rules.hotspots]
since = "90 days ago"
min_commits = 3
fail_on_quadrant = ["hotspot"]

[rules.packages]
max_distance = 0.85
severity = "warning"

[rules.deps]
fail_on_cycles = true

[rules.orphans]
enabled = false

[rules.class]
coupling_threshold = 15
inheritance_depth_threshold = 6
inheritance_children_threshold = 20
```

### Strict — for greenfield projects or quality-focused teams

Catches problems before they compound. Expect some friction in the first week as existing code is brought into compliance.

```toml
[rules.complexity]
cyclomatic_threshold = 6
cognitive_threshold = 10
weighted_threshold = 30

[rules.halstead]
volume_threshold = 500
difficulty_threshold = 20

[rules.npath]
npath_threshold = 100

[rules.hotspots]
since = "7 days ago"
min_commits = 1
fail_on_quadrant = ["hotspot", "churning_simple"]

[rules.packages]
max_distance = 0.5
severity = "error"

[rules.deps]
fail_on_cycles = true

[rules.orphans]
enabled = true
min_confidence = "high"
severity = "warning"

[rules.class]
coupling_threshold = 5
inheritance_depth_threshold = 3
inheritance_children_threshold = 7
```

## When to disable a rule

Disabling a rule is a legitimate choice in specific contexts. The table below helps you decide rather than guess.

| Rule | Disable when | Keep enabled when |
|---|---|---|
| `complexity.weighted` | No classes in your codebase (functional style, scripting) | Any OOP codebase |
| `hotspots` | No git history available, or running in a shallow-cloned CI without `fetch-depth: 0` | Any git repo with history |
| `packages` | Single-package project (metric ill-defined) | Multi-package projects in any supported language |
| `deps` | Very early prototype with intentionally fluid boundaries | Any project past the prototype stage |
| `orphans` | Always off as a CI gate. Enable for periodic cleanup audits only. | Never as a permanent gate — false positive rate is too high |
| `class.coupling` | No classes (functional, scripting) | Any OOP codebase |
| `class.inheritance.depth` | No inheritance used (composition-only architecture) | Any codebase using class hierarchies |
| `class.inheritance.children` | Plugin architectures where many subclasses are by design | Standard OOP codebases |
| `complexity.cyclomatic` | Never — this is the most fundamental complexity metric | Always |
| `complexity.cognitive` | Never — this catches readability problems CCX misses | Always |

**The two rules you should never disable** are `complexity.cyclomatic` and `complexity.cognitive`. If they're too noisy, raise the thresholds — don't turn them off. Complexity that goes unmeasured always grows.

## Severity levels

Each rule has a `severity` setting:

| Severity | Exit code | Meaning |
|---|---|---|
| `"error"` | 1 (fail) | Violation fails the lint run. Use for hard gates. |
| `"warning"` | 0 (pass) | Violation is reported but doesn't fail. Use for advisory rules or gradual adoption. |

To adopt slop gradually, start with everything set to `severity = "warning"`, review the output for a week, then promote rules to `"error"` one at a time.

```toml
# Gradual adoption example — everything advisory at first
[rules.complexity]
severity = "warning"

[rules.hotspots]
severity = "warning"

[rules.class]
severity = "warning"
```
