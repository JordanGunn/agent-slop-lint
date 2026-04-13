# Configuration Reference

This guide explains every configurable value in slop, what it means in practice, and when to change it. The goal is to help you tune slop to your project rather than disable it when a rule gets in the way.

slop reads config from `.slop.toml` (or `[tool.slop]` in `pyproject.toml`). Generate a starter config with `slop init`.

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

**Default threshold:** `WMC > 50`

**What the numbers mean:** A class with 10 methods averaging CCX=5 each has WMC=50. That's the boundary — it's a lot of logic in one place but not necessarily wrong. A class with WMC=150 is almost certainly a god class.

**When to raise it:** Large classes that are well-factored internally (clear method boundaries, low coupling between methods). Raising to 75–100 focuses on the truly egregious cases.

**When to lower it:** Projects enforcing single-responsibility strictly. WMC=30 catches classes that are starting to accumulate responsibilities.

**When to disable:** Projects with no classes (pure functional style, Go without receiver types, scripting). WMC is meaningless if there are no classes.

```toml
[rules.complexity]
weighted_threshold = 50
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

**Currently supports:** Go and Python only. Other languages are silently skipped.

**When to raise it:** Mature codebases where some packages are legitimately concrete and stable (e.g., utility packages). Raising to 0.85 focuses on extreme cases.

**When to lower it:** Projects with strict layered architecture. 0.5 catches packages drifting from the ideal early.

**When to disable:** Single-package projects, or languages other than Go and Python.

```toml
[rules.packages]
max_distance = 0.7
fail_on_zone = ["pain"]
severity = "warning"
```

### deps

**What it measures:** Dependency cycles between modules. Uses Tarjan's (1972) SCC algorithm on the import graph. Any cycle means two modules can't be changed or tested independently.

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

Copy one of these into your `.slop.toml` as a starting point.

### Default — balanced for most projects

```toml
[rules.complexity]
cyclomatic_threshold = 10
cognitive_threshold = 15
weighted_threshold = 50

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
weighted_threshold = 100

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
| `packages` | Single-package project, or language not Go/Python | Multi-package Go or Python projects |
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
